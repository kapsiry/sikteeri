# -*- coding: utf-8 -*-

from django.shortcuts import render_to_response
from django.template import RequestContext

from models import *
from forms import MembershipForm

def new_application(request, template_name='membership/new_application.html'):
    form = MembershipForm()
    if request.method == 'POST':
        form = MembershipForm(request.POST)
        if form.is_valid():
            membership = form.save()
            billing_cycle = BillingCycle(membership=membership)
            bill = Bill(cycle=billing_cycle)
            bill.send_as_email()
    return render_to_response(template_name, {"form": form},
                              context_instance=RequestContext(request))
