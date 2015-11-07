from __future__ import unicode_literals

from django import template
from django.http import QueryDict

register = template.Library()


class Page(template.Node):
    def __init__(self, field):
        self.page = field.replace('"', '')

    def render(self, context):
        """Return querystring part of URI
        >>> p = Page("5")
        >>> p.render({'querystring': {}})
        u'?page=5'
        >>> p.render({'querystring': {'sort':'id:1'}})
        u'?sort=id:1&page=5'
        """
        querystring = context.get('querystring', {})
        if isinstance(querystring, QueryDict):
            querystring = querystring.dict()
        page_obj = context.get('page_obj')
        if page_obj is None:
            querystring['page'] = unicode(self.page)
        elif self.page == 'previous':
            querystring['page'] = str(page_obj.previous_page_number())
        elif self.page == 'next':
            querystring['page'] = str(page_obj.next_page_number())
        else:
            querystring['page'] = str(context.get(self.page))
        return "?" + "&".join(["=".join(k) for k in querystring.items()])


def do_page(parser, token):
    """Get sorturl by sort field"""
    tag_name, field = token.split_contents()
    return Page(field)


register.tag('page', do_page)
