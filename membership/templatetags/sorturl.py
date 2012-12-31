from django import template

register = template.Library()


class SortUrl(template.Node):
    def __init__(self, field):
        self.sort_cycles = {
            u'id': [u'id', u'-id'],
            u'status': [u'status', u'-status'],
            u'name': [u'name', u'-last_name', u'name', u'last_name'],
            u'payer_name': [u'payer_name', u'-payer_name'],
            u'amount': [u'amount', u'-amount'],
            u'reference_number': [u'reference_number', u'-reference_number'],
            u'billingcycle': [u'billingcycle', u'-billingcycle'],
            u'comment': [u'comment', u'-comment'],
            u'cycle': [u'start', u'end'],
            u'sum': [u'sum', u'-sum'],
            u'due_date': [u'bill__due_date', u'-bill__due_date']
        }
        self.page = template.Variable('page')
        self.sort = template.Variable('sort')
        self.search_query = template.Variable('search_query')
        self.field = field.replace('"', '').replace("'", '').strip()

    def render(self, context):
        try:
            page = self.page.resolve(context)
        except:
            page = 1
        try:
            sort = self.sort.resolve(context)
        except:
            sort = None
        try:
            search_query = self.search_query(context)
        except:
            search_query = None
        sort_cycle = None
        for cycle in self.sort_cycles:
            if self.field == cycle:
                sort_cycle = self.sort_cycles[cycle]
                break
        if sort_cycle:
            if sort in sort_cycle:
                if sort_cycle.index(sort) == (len(sort_cycle) - 1):
                    sort = sort_cycle[0]
                else:
                    sort = sort_cycle[sort_cycle.index(sort) + 1]
            else:
                sort = sort_cycle[0]
        else:
            sort = None
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
