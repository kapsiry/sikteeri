# encoding: UTF-8

# Origin:
# http://djangosnippets.org/snippets/161/

import logging
logger = logging.getLogger("SQLLogMiddleware")

from django.db import connection
from django.template import Template, Context

class SQLLogMiddleware:
    def process_response ( self, request, response ): 
        time = 0.0
        for q in connection.queries:
            if 'FROM "django_session"' in q['sql'] or 'FROM "auth_user"' in q['sql'] :
                continue
            time += float(q['time'])
            logger.debug("SQL query (%s). Finished in %f seconds." % (q['sql'], time))
        return response
