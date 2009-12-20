# -*- coding: utf-8 -*-

import logging

from django.conf import settings
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.template import RequestContext
from django.forms import ModelForm
from django.contrib.auth.decorators import login_required
from django.contrib.comments.models import Comment

from models import *
from forms import MembershipForm
from utils import log_change

def new_application(request, template_name='membership/new_application.html'):
    if request.method == 'POST':
        form = MembershipForm(request.POST)
        if form.is_valid():
            logging.info('A new membership application from %s:\n %s' % (request.META['REMOTE_ADDR'], repr(form.cleaned_data)))
            membership = form.save()
    else:
        form = MembershipForm()

    return render_to_response(template_name, {"form": form},
                              context_instance=RequestContext(request))

def check_alias_availability(request):
    pass

# XXX Replace with a generic view in URLconf
@login_required
def membership_list(request, template_name='membership/membership_list.html'):
    return render_to_response(template_name, {'members': Membership.objects.all()},
                              context_instance=RequestContext(request))

# XXX Replace with a generic view in URLconf
@login_required
def membership_list_new(request, template_name='membership/membership_list.html'):
    return render_to_response(template_name,
        {'members': Membership.objects.filter(status__exact='N')},
        context_instance=RequestContext(request))

@login_required
def membership_edit_inline(request, id, template_name='membership/membership_edit_inline.html'):
    membership = get_object_or_404(Membership, id=id)

    # XXX: I hate this. Wasn't there a shortcut for creating a form from instance?
    class Form(ModelForm):
        class Meta:
            model = Membership

    if request.method == 'POST':
        form = Form(request.POST, instance=membership)
        before = membership.__dict__.copy() # Otherwise save() will change the dict, since we have given form this instance
        form.save()
        after = membership.__dict__
        if form.is_valid():
            log_change(membership, request.user, before, after)
    else:
        form =  Form(instance=membership)
    return render_to_response(template_name, {'form': form, 'membership': membership},
                                  context_instance=RequestContext(request))

def membership_edit(request, id, template_name='membership/membership_edit.html'):
    # XXX: Inline template name is hardcoded in template :/
    return membership_edit_inline(request, id, template_name)

def membership_preapprove(request, id):
    membership = get_object_or_404(Membership, id=id)
    membership.status = 'P' # XXX hardcoding
    membership.save()
    comment = Comment()
    comment.content_object = membership
    comment.user = request.user
    comment.comment = "Preapproved"
    comment.site_id = settings.SITE_ID
    comment.submit_date = datetime.now()
    comment.save()
    log_change(membership, request.user, change_message="Preapproved")
    return redirect('membership_edit', id)

def membership_preapprove_many(request, id_list):
    for id in id_list:
        membership_preapprove(id)

def membership_approve(request, id):
    membership = get_object_or_404(Membership, id=id)
    membership.status = 'A' # XXX hardcoding
    membership.save()
    comment = Comment()
    comment.content_object = membership
    comment.user = request.user
    comment.comment = "Approved"
    comment.site_id = settings.SITE_ID
    comment.submit_date = datetime.now()
    comment.save()
    billing_cycle = BillingCycle(membership=membership)
    billing_cycle.save() # Creating an instance does not touch db and we need and id for the Bill
    bill = Bill(cycle=billing_cycle)
    bill.save()
    bill.send_as_email()
    log_change(object, request.user, change_message="Approved")
    return redirect('membership_edit', id)

def membership_preapprove_many(request, id_list):
    for id in id_list:
        membership_preapprove(id)

def handle_json(request):
    msg = cjson.decode(request.raw_post_data)
    funcs = {'PREAPPROVE': membership_preapprove_many}
    return funcs[content['requestType']](request, msg['payload'])
