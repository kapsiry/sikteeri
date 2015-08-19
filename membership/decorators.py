#!/usr/bin/env python
# encoding: utf-8
"""
decorators.py

"""

from django.contrib.auth import authenticate
from django.http import HttpResponse, HttpResponseForbidden
from django.conf import settings

from sikteeri.iptools import IpRangeList

import base64


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def trusted_host_required(view_func):
    """ decorator which checks remote address """
    def decorator(request, *args, **kwargs):
        if not hasattr(settings, 'TRUSTED_HOSTS') or not settings.TRUSTED_HOSTS:
            settings.TRUSTED_HOSTS = []
        ip = get_client_ip(request)
        allowed = IpRangeList(*settings.TRUSTED_HOSTS)
        if ip in allowed:
            return view_func(request, *args, **kwargs)
        response = HttpResponseForbidden("Access denied")
        return response
    return decorator

def basic_auth_required(view_func):
    # http://djangosnippets.org/snippets/448/
    """ decorator which performs basic http token authentication """
    def _auth(request, *args, **kwargs):
        if 'HTTP_AUTHORIZATION' in request.META:
            auth = request.META['HTTP_AUTHORIZATION'].split()
            if len(auth) == 2:
                if auth[0].lower() == "basic":
                    uname, passwd = base64.b64decode(auth[1]).split(':')
                    user = authenticate(username=uname, password=passwd)
                    if user is not None:
                        if user.is_active:
                            return view_func(request, *args, **kwargs)
        response = HttpResponse("Authorization Required", status=401)
        response['WWW-Authenticate'] = 'Basic realm="Secure Area"'
        return response
    return _auth


def main():
    pass

if __name__ == '__main__':
    main()
