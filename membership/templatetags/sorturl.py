from django import template

register = template.Library()

sort_cycles = {
    u'id': [u'id', u'-id'],
    u'status': [u'status', u'-status'],
    u'name': [u'name', u'last_name', u'-name', u'-last_name'],
    u'payer_name': [u'payer_name', u'-payer_name'],
    u'amount': [u'amount', u'-amount'],
    u'reference_number': [u'reference_number', u'-reference_number'],
    u'billingcycle': [u'billingcycle', u'-billingcycle'],
    u'comment': [u'comment', u'-comment'],
    u'cycle': [u'start', u'end'],
    u'sum': [u'sum', u'-sum'],
    u'due_date': [u'bill__due_date', u'-bill__due_date']
}

class SortUrl(template.Node):
    def __init__(self, field):
        self.field = field.replace('"', '').replace("'", '').strip()

    def render(self, context):
        page = context.get('page', 1)
        sort = context.get('sort')
        search_query = context.get('search_query', None)
        sort_cycle = None
        if self.field in sort_cycles:
            sort_cycle = sort_cycles[self.field]
            print("SORT: %s" % sort)
            if sort in sort_cycle:
                if sort_cycle.index(sort) == (len(sort_cycle) - 1):
                    sort = sort_cycle[0]
                else:
                    sort = sort_cycle[sort_cycle.index(sort) + 1]
            else:
                sort = sort_cycle[0]
        if sort and search_query:
            return '?page=%s&query=%s&sort=%s' % (page, search_query, sort)
        elif sort:
            return '?page=%s&sort=%s' % (page, sort)
        elif search_query:
            return '?page=%s&query=%s' % (page, search_query)
        else:
            return '?page=%s' % (page)


def do_sorturl(parser, token):
    """Get sorturl by sort field"""
    try:
        tag_name, field = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError(
            "%s tag requires page, search_query and sort arguments" % tag_name)
    return SortUrl(field)


register.tag('sorturl', do_sorturl)
