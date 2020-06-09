#!/usr/bin/env python
# encoding: utf-8

from .version import VERSION

class GitVersionHeaderMiddleware(object):
    """
    Set a X-Sikteeri-Version header to the response

    The X-Sikteeri-Version header is intended to convey the deployed version
    number of the project reliably.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        response['X-Sikteeri-Version'] = VERSION
        return response
