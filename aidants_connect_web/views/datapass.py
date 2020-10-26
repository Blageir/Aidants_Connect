import logging

from django.http import HttpResponse, HttpResponseForbidden

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


def receiver(request):
    if request.META["HTTP_AUTHORIZATION"] != "good_token":
        log.info("403: Bad authorization header for datapass call")
        return HttpResponseForbidden()

    # Check body
    # create orga
    # if orga already in : do not create orga
    # send email to the team
    return HttpResponse(status=202)
