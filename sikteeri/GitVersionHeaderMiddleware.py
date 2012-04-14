#!/usr/bin/env python
# encoding: utf-8

from version import VERSION

class GitVersionHeaderMiddleware(object):
    """
    Set a X-Sikteeri-Version header to the response

    The X-Sikteeri-Version header is intended to convey the deployed version
    number of the project reliably.
    """
    def process_response(self, request, response):
        response['X-Sikteeri-Version'] = VERSION
        return response
