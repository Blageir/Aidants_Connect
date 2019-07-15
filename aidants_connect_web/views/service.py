import logging
import jwt
import time
import re
from datetime import date
from secrets import token_urlsafe

from django.http import HttpResponseForbidden, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError
from django.forms.models import model_to_dict
from django.conf import settings
from django.utils import timezone
from django.contrib import messages
from django.contrib.messages import get_messages

from aidants_connect_web.models import (
    Connection,
    Mandat,
    Usager,
    CONNECTION_EXPIRATION_TIME,
)
from aidants_connect_web.forms import UsagerForm, MandatForm


logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


def humanize_demarche_names(list_of_machine_names):
    human_names = []
    for p in list_of_machine_names:
        for category in settings.DEMARCHES:
            for element in category[1]:
                if element[0] == p:
                    human_names.append(element[1])
    return human_names


def home_page(request):
    random_string = token_urlsafe(10)
    return render(
        request, "aidants_connect_web/home_page.html", {"random_string": random_string}
    )


@login_required
def logout_page(request):
    logout(request)
    return redirect(settings.LOGOUT_REDIRECT_URL)


@login_required
def dashboard(request):
    messages = get_messages(request)
    user = request.user
    mandats = Mandat.objects.all().filter(aidant=request.user).order_by("creation_date")

    for mandat in mandats:
        mandat.perimeter_names = humanize_demarche_names(mandat.perimeter)

    return render(
        request,
        "aidants_connect_web/dashboard.html",
        {"user": user, "mandats": mandats, "messages": messages},
    )


@login_required
def mandat(request):
    user = request.user
    form = MandatForm()

    if request.method == "GET":
        return render(
            request,
            "aidants_connect_web/mandat/mandat.html",
            {"user": user, "form": form},
        )

    else:
        form = MandatForm(request.POST)

        if form.is_valid():
            request.session["mandat"] = form.cleaned_data
            return redirect("fc_authorize")
        else:
            return render(
                request,
                "aidants_connect_web/mandat/mandat.html",
                {"user": user, "form": form},
            )


@login_required
def recap(request):
    user = request.user
    # TODO check if user already exists via sub

    usager_data = request.session.get("usager")

    usager = Usager(
        given_name=usager_data.get("given_name"),
        family_name=usager_data.get("family_name"),
        birthdate=usager_data.get("birthdate"),
        gender=usager_data.get("gender"),
        birthplace=usager_data.get("birthplace"),
        birthcountry=usager_data.get("birthcountry"),
        # TODO fix identity provider example
        # email=usager_data.get("email"),
        sub=usager_data.get("sub"),
    )

    if usager_data.get("email"):
        usager.email = usager_data.get("email")

    mandat = request.session.get("mandat")

    if request.method == "GET":
        demarches = humanize_demarche_names(mandat["perimeter"])

        return render(
            request,
            "aidants_connect_web/mandat/recap.html",
            {
                "user": user,
                "usager": usager,
                "demarches": demarches,
                "duration": mandat["duration"],
            },
        )

    else:
        form = request.POST
        if form.get("personal_data") and form.get("brief"):
            mandat["aidant"] = user
            try:
                usager.save()
            except IntegrityError as e:
                log.error("Error happened in Recap")
                log.error(e)
                messages.error(request, f"The FranceConnect ID is not complete : {e}")
                return redirect("dashboard")

            mandat["usager"] = usager

            new_mandat = Mandat.objects.create(**mandat)

            messages.success(request, "Le mandat a été créé avec succès !")

            return redirect("dashboard")

        else:
            return render(
                request,
                "aidants_connect_web/mandat/recap.html",
                {
                    "user": user,
                    "usager": usager,
                    "demarche": demarches,
                    "duration": mandat["duration"],
                    "error": "Vous devez accepter les conditions du mandat.",
                },
            )


@login_required
def authorize(request):
    fc_callback_url = settings.FC_AS_FI_CALLBACK_URL

    if request.method == "GET":
        state = request.GET.get("state", False)
        nonce = request.GET.get("nonce", False)
        code = token_urlsafe(64)
        this_connexion = Connection(state=state, code=code, nonce=nonce)
        this_connexion.save()

        if state is False:
            log.info("403: There is no state")
            return HttpResponseForbidden()

        aidant = request.user
        usagers_id = Mandat.objects.values_list("usager", flat=True)
        # TODO Do we send the whole usager ? or only first name and last name and sub ?
        usagers = [Usager.objects.get(id=usager_id) for usager_id in usagers_id]
        return render(
            request,
            "aidants_connect_web/authorize.html",
            {"state": state, "usagers": usagers, "aidant": aidant},
        )

    else:
        this_state = request.POST.get("state")
        try:
            that_connection = Connection.objects.get(state=this_state)
            state = that_connection.state
            code = that_connection.code
        except ObjectDoesNotExist:
            log.info("No connection corresponds to the state:")
            log.info(this_state)
            return HttpResponseForbidden()

        # TODO check if connection has not expired

        that_connection.sub_usager = request.POST.get("chosen_user")
        that_connection.save()

        return redirect(f"{fc_callback_url}?code={code}&state={state}")


# Due to `no_referer` error
# https://docs.djangoproject.com/en/dev/ref/csrf/#django.views.decorators.csrf.csrf_exempt
@csrf_exempt
def token(request):
    fc_callback_url = settings.FC_AS_FI_CALLBACK_URL
    fc_client_id = settings.FC_AS_FI_ID
    fc_client_secret = settings.FC_AS_FI_SECRET
    host = settings.HOST

    if request.method == "GET":
        log.info("This method is a get")
        return HttpResponse("You did a GET on a POST only route")

    rules = [
        request.POST.get("grant_type") == "authorization_code",
        request.POST.get("redirect_uri") == fc_callback_url,
        request.POST.get("client_id") == fc_client_id,
        request.POST.get("client_secret") == fc_client_secret,
    ]
    if not all(rules):
        log.info("403: Rules are not all abided")
        log.info(rules)
        return HttpResponseForbidden()

    code = request.POST.get("code")

    try:
        connection = Connection.objects.get(code=code)
    except ObjectDoesNotExist:
        log.info("403: /token No connection corresponds to the code")
        log.info(code)
        return HttpResponseForbidden()

    if connection.expiresOn < timezone.now():
        log.info("403: Code expired")
        return HttpResponseForbidden()
    id_token = {
        # The audience, the Client ID of your Auth0 Application
        "aud": fc_client_id,
        # The expiration time. in the format "seconds since epoch"
        # TODO Check if 10 minutes is not too much
        "exp": int(time.time()) + CONNECTION_EXPIRATION_TIME * 60,
        # The issued at time
        "iat": int(time.time()),
        # The issuer,  the URL of your Auth0 tenant
        "iss": host,
        # The unique identifier of the user
        "sub": connection.sub_usager,
        "nonce": connection.nonce,
    }

    encoded_id_token = jwt.encode(id_token, fc_client_secret, algorithm="HS256")
    access_token = token_urlsafe(64)
    connection.access_token = access_token
    connection.save()
    response = {
        "access_token": access_token,
        "expires_in": 3600,
        "id_token": encoded_id_token.decode("utf-8"),
        "refresh_token": "5ieq7Bg173y99tT6MA",
        "token_type": "Bearer",
    }

    definite_response = JsonResponse(response)
    return definite_response


def user_info(request):

    auth_header = request.META.get("HTTP_AUTHORIZATION")

    if not auth_header:
        log.info("403: Missing auth header")
        return HttpResponseForbidden()

    pattern = re.compile(r"^Bearer\s([A-Z-a-z-0-9-_/-]+)$")
    if not pattern.match(auth_header):
        log.info("Auth header has wrong format")
        return HttpResponseForbidden()

    auth_token = auth_header[7:]
    connection = Connection.objects.get(access_token=auth_token)

    if connection.expiresOn < timezone.now():
        return HttpResponseForbidden()
    usager = Usager.objects.get(sub=connection.sub_usager)
    usager = model_to_dict(usager)
    del usager["id"]
    birthdate = usager["birthdate"]
    birthplace = usager["birthplace"]
    birthcountry = usager["birthcountry"]
    usager["birthplace"] = str(birthplace)
    usager["birthcountry"] = str(birthcountry)
    usager["birthdate"] = str(birthdate)

    return JsonResponse(usager, safe=False)
