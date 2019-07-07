

from django import template
from django.http import QueryDict

register = template.Library()

sort_cycles = {
    'id': ['id', '-id'],
    'status': ['status', '-status'],
    'bill_name': ['membership__person__first_name',
                  'membership__person__last_name',
                  '-membership__person__first_name',
                  '-membership__person__last_name'],
    'name': ['person__first_name', 'person__last_name', '-person__first_name', '-person__last_name'],
    'payer_name': ['payer_name', '-payer_name'],
    'amount': ['amount', '-amount'],
    'reference_number': ['reference_number', '-reference_number'],
    'billingcycle': ['billingcycle', '-billingcycle'],
    'comment': ['comment', '-comment'],
    'cycle': ['start', '-start', 'end', '-end'],
    'sum': ['sum', '-sum'],
    'due_date': ['bill__due_date', '-bill__due_date']
}


def lookup_sort(sort):
    """Find order by term by sort string
    >>> lookup_sort("id:1")
    u'id'
    >>> lookup_sort(None)
    >>> lookup_sort("id:2")
    u'-id'
    >>> lookup_sort("foo:1")
    >>> lookup_sort("id:3")
    >>> lookup_sort("id:a")
    """
    if sort is None:
        return None
    assert isinstance(sort, str)
    key, __, index = sort.partition(':')
    try:
        return sort_cycles[key][int(index)-1]
    except (IndexError, KeyError, ValueError):
        return None


def next_sort(sort):
    """Find next value from sort_cycles
    >>> next_sort("id:1")
    u'id:2'
    >>> next_sort("id:2")
    u'id:1'
    >>> next_sort("id:3")
    u'id:1'
    >>> next_sort("id:a")
    u'id:1'
    >>> next_sort("asdf:xyz")
    """
    if sort is None:
        return None
    assert isinstance(sort, str)
    key, __, index = sort.partition(':')
    try:
        available_sorts = sort_cycles[key]
        max_index = len(available_sorts)
        try:
            cur_index = int(index)
            if cur_index > max_index:
                next_index = 1
            else:
                next_index = 1 + cur_index % max_index
        except ValueError:
            next_index = 1
        return "{key}:{index}".format(key=key, index=next_index)
    except (IndexError, KeyError):
        return None


class SortUrl(template.Node):
    def __init__(self, field):
        self.field = field.replace('"', '').replace("'", '').strip()
        if self.field not in sort_cycles:
            raise ValueError("Unknown sort key")

    def render(self, context):
        """Return querystring part of URI
        >>> s = SortUrl('id')
        >>> s.render({'querystring': {}})
        u'?sort=id:1'
        >>> s.render({'querystring': {'sort':'id:1'}})
        u'?sort=id:2'
        >>> s.render({'querystring': {'sort':'name:1'}})
        u'?sort=id:1'
        >>> s = SortUrl('asdf')
        Traceback (most recent call last):
        ValueError: Unknown sort key
        """
        querystring = context.get('querystring', {})
        if isinstance(querystring, QueryDict):
            querystring = querystring.dict()
        sort = querystring.get('sort', "{key}:None".format(key=self.field))
        key, __, __ = sort.partition(':')

        next_sort_value = next_sort(sort)

        if key == self.field and next_sort_value is not None:
            querystring['sort'] = next_sort_value
        else:
            querystring['sort'] = "{key}:1".format(key=self.field)
        return "?" + "&".join(["=".join(k) for k in list(querystring.items())])


def do_sorturl(parser, token):
    """Get sorturl by sort field"""
    tag_name, field = token.split_contents()
    return SortUrl(field)


register.tag('sorturl', do_sorturl)
