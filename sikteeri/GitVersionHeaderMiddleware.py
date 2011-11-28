#!/usr/bin/env python
# encoding: utf-8

from version import VERSION

class GitVersionHeaderMiddleware(object):
    """
    Set a X-Git-SHA1 header to the response

    The X-Git-SHA1 header is intended to convey the deployed version
    number of the project reliably.
    """
    def process_response(self, request, response):
        response['X-Git-SHA1'] = VERSION
        return response
