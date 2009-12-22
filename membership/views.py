# -*- coding: utf-8 -*-

import logging

from django.conf import settings
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.template import RequestContext
from django.forms import ModelForm
from django.contrib.auth.decorators import login_required
from django.contrib.comments.models import Comment
from django.db import transaction
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponseForbidden

from models import *
from forms import PersonApplicationForm, OrganizationApplicationForm
from utils import log_change


def new_application(request, template_name='membership/choose_membership_type.html'):
    return render_to_response(template_name, {},
                              context_instance=RequestContext(request))


def contact_from_form(f, prefix=''):
    if len(prefix) > 0:
        prefix = prefix + '_'
    c = Contact(street_address=f['%sstreet_address' % prefix],
                postal_code=f['%spostal_code' % prefix],
                post_office=f['%spost_office' % prefix],
                country=f['%scountry' % prefix],
                phone=f['%sphone' % prefix],
                sms=f['%ssms' % prefix],
                email=f['%semail' % prefix],
                homepage=f['%shomepage' % prefix])
    
    if f.has_key('organization_name'):
        c.organization_name = f['%sorganization_name' % prefix]
    else:
        c.first_name = f['%sfirst_name' % prefix]
        c.given_names = f['%sgiven_names' % prefix]
        c.last_name = f['%slast_name' % prefix]
    return c


@transaction.commit_manually
def person_application(request, template_name='membership/new_person_application.html'):
    if request.method == 'POST':
        application_form = PersonApplicationForm(request.POST)
        
        if application_form.is_valid():
            f = application_form.cleaned_data
            try:
                person = contact_from_form(f)
                person.save()
                membership = Membership(type='P', status='N',
                                        person=person,
                                        nationality=f['nationality'],
                                        municipality=f['municipality'],
                                        extra_info=f['extra_info'])
                membership.save()
                transaction.commit()
                logging.info("New application %s from %s:." % (str(person), request.META['REMOTE_ADDR']))
                return redirect('new_person_application_success')                
            except Exception, e:
                transaction.rollback()
                logging.error("Encountered %s" % repr(e))
                logging.error("Transaction rolled back while trying to process %s." % repr(application_form.cleaned_data))
                return redirect('new_application_fail')
    else:
        application_form = PersonApplicationForm()
    return render_to_response(template_name, {"form": application_form},
                              context_instance=RequestContext(request))

@transaction.commit_manually
def organization_application(request, template_name='membership/new_organization_application.html'):
    if request.method == 'POST':
        application_form = OrganizationApplicationForm(request.POST)
        
        if application_form.is_valid():
            f = application_form.cleaned_data
            try:
                organization = contact_from_form(f)
                organization.save()
                membership = Membership(type='O', status='N',
                                        organization=organization,
                                        nationality=f['nationality'],
                                        municipality=f['municipality'],
                                        extra_info=f['extra_info'])
                membership.save()
                transaction.commit()
                request.session.set_expiry(0) # make this expire when the browser exits
                request.session['new_membership_id'] = membership.id
                logging.debug("Registered session, membership id: %i." %request.session['new_membership_id'])
                logging.info("New application %s from %s:." % (str(organization), request.META['REMOTE_ADDR']))
                return redirect('organization_application_add_contacts', membership.id)
            except Exception, e:
                transaction.rollback()
                logging.error("Encountered %s" % repr(e))
                logging.error("Transaction rolled back while trying to process %s." % repr(application_form.cleaned_data))
                return redirect('new_application_fail')
    else:
        application_form = OrganizationApplicationForm()
    return render_to_response(template_name, {"form": application_form},
                              context_instance=RequestContext(request))

def organization_application_add_contacts(request, id, template_name='membership/organization_application_add_contacts.html'):
    if str(request.session['new_membership_id']) != str(id):
        return HttpResponseForbidden()
    return render_to_response(template_name, {"membership": Membership.objects.get(id=id)},
                              context_instance=RequestContext(request))

def organization_application_contact_create_update(request, type, id, template_name='membership/organization_application_contact_create_update.html'):
    if str(request.session["new_membership_id"]) != str(id):
        return HttpResponseForbidden("Access denied")
    if type not in ['person', 'billing_contact', 'tech_contact']:
        return HttpResponseForbidden("Access denied")
    
    class Form(ModelForm):
        class Meta:
            model = Contact
            fields = ('first_name', 'given_names', 'last_name', 'street_address',
                      'postal_code', 'post_office', 'country', 'phone', 'sms',
                      'email', 'homepage')
    
    membership = Membership.objects.get(id=id)
    contact = None
    contact_form = None
    contact_type = ''
    if type == 'person':
        contact = membership.person
        contact_type = _('Administrative contact')
    elif type == 'billing_contact':
        contact = membership.billing_contact
        contact_type = _('Billing contact')
    elif type == 'tech_contact':
        contact = membership.tech_contact
        contact_type = _('Technical contact')
    
    if request.method == 'POST':
        form = Form(request.POST, instance=contact)
        form.save()
        if type == 'person':
            membership.person = form.instance
        elif type == 'billing_contact':
            membership.billing_contact = form.instance
        elif type == 'tech_contact':
            membership.tech_contact = form.instance
        membership.save()
        return redirect('organization_application_add_contacts', membership.id)
    else:
        if contact is not None:
            contact_form = Form(instance=contact)
        else:
            contact_form = Form()
    
    return render_to_response(template_name, {"form": contact_form,
                                              "type": type,
                                              "contact_type": contact_type},
                              context_instance=RequestContext(request))

def check_alias_availability(request):
    pass

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
