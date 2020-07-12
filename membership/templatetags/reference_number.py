# -*- coding: utf-8 -*-

from django import template

from django.template.defaultfilters import stringfilter
from django.utils.safestring import mark_safe
from membership.reference_numbers import group_right

register = template.Library()


@register.filter
@stringfilter
def fref(number, length):
    """
    Number is the reference number, length is the max reference number length anticipated.
    """
    ref = group_right(number)
    length = int(length)
    if len(ref) >= length:
        return ref
    else:
        ret = ""
        for i in range(0, int(length) - len(ref)):
            ret = ret + "&nbsp;"
        return mark_safe(ret + ref)
