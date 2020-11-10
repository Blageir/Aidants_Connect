import logging

from django.conf import settings
from django.core.mail import send_mail
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseBadRequest

from aidants_connect_web.models import Organisation

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


def receiver(request):

    if request.META["HTTP_AUTHORIZATION"] != settings.DATAPASS_KEY:
        log.info("403: Bad authorization header for datapass call")
        return HttpResponseForbidden()

    if request.method != "POST":
        return HttpResponse("This is a POST only route")

    parameters = {
        "contact_name": request.POST.get("contact_name"),
        "contact_email": request.POST.get("contact_email"),
        "data_pass_id": request.POST.get("data_pass_id"),
        "organization_name": request.POST.get("organization_name"),
        "organization_siret": request.POST.get("organization_siret"),
        "organization_address": request.POST.get("organization_address"),
    }
    for parameter, value in parameters.items():
        if not value:
            error_message = f"400 Bad request: There is no {parameter} @ datapass"
            log.info(error_message)
            return HttpResponseBadRequest()

    try:
        this_organisation = Organisation.objects.create(
            name=parameters["organization_name"],
            siret=parameters["organization_siret"],
            address=parameters["organization_address"],
            contact_name=parameters["contact_name"],
            contact_email=parameters["contact_email"],
            datapass_id=parameters["data_pass_id"],
        )
    except ValueError as e:
        log.info(f"{e} @ datapass")
        return HttpResponseBadRequest()

    send_mail(
        subject="Une nouvelle structure",
        message=f"""
            la structure {this_organisation.name} vient
            d'être validée pour avoir des accès à Aidants Connect.
            Merci de contacter {this_organisation.contact_name}
            - {this_organisation.contact_email}
        """,
        from_email=settings.DATAPASS_FROM_EMAIL,
        recipient_list=["to@example.com"],
        fail_silently=False,
    )

    return HttpResponse(status=202)
