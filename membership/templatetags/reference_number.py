# -*- coding: utf-8 -*-

from django import template
register = template.Library()
from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe

from membership.reference_numbers import group_right

@register.filter
@stringfilter
def fref(number, length):
    "Number is the reference number, length is the max reference number length anticipated."
    ref = group_right(number)
    if len(ref) >= length:
        return ref
    else:
        ret = u""
        for i in xrange(0, int(length) - len(ref)):
            ret = ret + u"&nbsp;"
        return mark_safe(ret + ref)
