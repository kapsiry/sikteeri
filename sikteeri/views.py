# -*- coding: utf-8 -*-

import logging

logger = logging.getLogger("sikteeri.views")

from django.conf import settings
from django.shortcuts import redirect, render
from django.utils.translation import ugettext_lazy as _

from sikteeri.version import VERSION


def frontpage(request):
    if settings.MAINTENANCE_MESSAGE is None:
        if not request.user.is_authenticated:
            return redirect('new_application')
        return render(request, 'frontpage.html',
                      dict(title=_('Django and the jazz cigarette'),
                           version=VERSION))

    else:
        return render(request, 'maintenance_message.html',
                      {"title": _('Under maintenance'),
                       "maintenance_message": settings.MAINTENANCE_MESSAGE})
