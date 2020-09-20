import logging
from urllib.parse import urlencode, urljoin

import requests
from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.http import HttpResponseBadRequest, HttpResponseServerError
from django.shortcuts import render, redirect

from procountor.models import APIToken

logger = logging.getLogger("procountor.views")


@permission_required('procountor.can_add_procountor_token')
def procountor_login(request, **kwargs):
    """
    Redirect user to Procountor M2M login page
    """
    params = {
        "response_type": "code",
        "client_id": settings.PROCOUNTOR_CLIENT_ID,
        "redirect_uri": settings.PROCOUNTOR_REDIRECT_URL,
    }
    url = urljoin(settings.PROCOUNTOR_KEYLOGIN_URL, "?{}".format(urlencode(params)))
    return redirect(url)


@permission_required('procountor.can_add_procountor_token')
def procountor_login_return(request, **kwargs):
    """
    User is redirected back from Procountor login page
    We need to exchange temporary authorization_code to api_token
    """

    if request.method != 'GET':
        return HttpResponseBadRequest("Invalid request")

    code = request.GET.get("code", None)
    expires_in = request.GET.get("expires_in", None)
    if not code or not expires_in:
        return HttpResponseBadRequest("Invalid request")

    token_request_data = {
        "grant_type": "authorization_code",
        "client_id": settings.PROCOUNTOR_CLIENT_ID,
        "client_secret": settings.PROCOUNTOR_CLIENT_SECRET,
        "redirect_uri": settings.PROCOUNTOR_REDIRECT_URL,
        "code": code
    }

    response = requests.post("{}/oauth/key".format(settings.PROCOUNTOR_API_URL), data=token_request_data)

    if response.status_code != 200:
        logger.error("Failed to exchange Procountor code to api key: %s", response.content)
        return HttpResponseServerError("API key exchange failed")

    token_data = response.json()

    if 'api_key' not in token_data:
        return HttpResponseServerError("Invalid response from Procountor API")

    api_key_object = APIToken.objects.first()

    if not api_key_object:
        api_key_object = APIToken()

    api_key_object.api_key = token_data["api_key"]

    api_key_object.save()

    return render(request=request, template_name="procountor/procountor_token_added.html")
