# -*- coding: utf-8 -*-

import logging

from time import sleep

from django.conf import settings
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.template import RequestContext
from django.forms import ModelForm
from django.contrib.auth.decorators import login_required
from django.contrib.comments.models import Comment
from django.db import transaction
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponse, HttpResponseForbidden

import simplejson

from models import *
from forms import PersonApplicationForm, OrganizationApplicationForm, PersonContactForm
from utils import log_change


def new_application(request, template_name='membership/choose_membership_type.html'):
    return render_to_response(template_name, {},
                              context_instance=RequestContext(request))

def contact_from_dict(d):
    if d is None:
        return None
    
    try:
        c = Contact(street_address=d['street_address'],
                    postal_code=d['postal_code'],
                    post_office=d['post_office'],
                    country=d['country'],
                    phone=d['phone'],
                    sms=d['sms'],
                    email=d['email'],
                    homepage=d['homepage'])
    except:
        return None
    
    if d.has_key('organization_name') and len(d['organization_name']) > 5:
        c.organization_name = d['organization_name']
    else:
        c.first_name = d['first_name']
        c.given_names = d['given_names']
        c.last_name = d['last_name']
    return c

@transaction.commit_manually
def person_application(request, template_name='membership/new_person_application.html'):
    if request.method == 'POST':
        application_form = PersonApplicationForm(request.POST)
        
        if application_form.is_valid():
            f = application_form.cleaned_data
            try:
                person = contact_from_dict(f)
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

def organization_application(request, template_name='membership/new_organization_application.html'):
    if request.method == 'POST':
        form = OrganizationApplicationForm(request.POST)
        
        if form.is_valid():
            f = form.cleaned_data
            organization = contact_from_dict(f)
            membership = Membership(type='O', status='N',
                                    nationality=f['nationality'],
                                    municipality=f['municipality'],
                                    extra_info=f['extra_info'])

            request.session.set_expiry(0) # make this expire when the browser exits
            request.session['membership'] = membership.__dict__.copy()
            request.session['organization'] = organization.__dict__.copy()
            return redirect('organization_application_add_contact', 'person')
    else:
        form = OrganizationApplicationForm()
    return render_to_response(template_name, {"form": form,
                                              "title": _('Organization application')},
                              context_instance=RequestContext(request))

def organization_application_add_contact(request, contact_type, template_name='membership/new_organization_application_add_contact.html'):
    forms = ['person', 'billing_contact', 'tech_contact']
    if contact_type not in forms:
        return HttpResponseForbidden("Access denied")
    
    if contact_type == 'person':
        type_text = 'Administrative contact'
    elif contact_type == 'billing_contact':
        type_text = 'Billing contact'
    elif contact_type == 'tech_contact':
        type_text = 'Technical contact'
    
    if request.method == 'POST':
        form = PersonContactForm(request.POST)
        if form.is_valid() or len(form.changed_data) == 0:
            if form.is_valid():
                f = form.cleaned_data
                contact = contact_from_dict(f)
                request.session[contact_type] = contact.__dict__.copy()
            else:
                request.session[contact_type] = None
            next_idx = forms.index(contact_type) + 1
            if next_idx == len(forms):
                return redirect('organization_application_review')
            return redirect('organization_application_add_contact', forms[next_idx])
    else:
        if request.session.has_key(contact_type):
            form = PersonApplicationForm(request.session[contact_type])
        else:
            form = PersonApplicationForm()
    return render_to_response(template_name, {"form": form, "contact_type": type_text,
                                              "step_number": forms.index(contact_type) + 2,
                                              "title": _('Organization application') + ' - ' + type_text},
                              context_instance=RequestContext(request))

def organization_application_review(request, template_name='membership/new_organization_application_review.html'):
    membership = Membership(type='O', status='N',
                            nationality=request.session['membership']['nationality'],
                            municipality=request.session['membership']['municipality'],
                            extra_info=request.session['membership']['extra_info'])
    
    def get_or_none(dict, key):
        if dict.has_key(key):
            return dict[key]
        else:
            return None
    
    organization = contact_from_dict(request.session['organization'])
    person = contact_from_dict(get_or_none(request.session, 'person'))
    billing_contact = contact_from_dict(get_or_none(request.session, 'billing_contact'))
    tech_contact = contact_from_dict(get_or_none(request.session, 'tech_contact'))
    
    forms = []
    combo_dict = request.session['membership']
    for k, v in request.session['organization'].items():
        combo_dict[k] = v
    forms.append(OrganizationApplicationForm(combo_dict))
    if person:
        forms.append(PersonContactForm(request.session['person']))
        forms[-1].name = _("Administrative contact")
    if billing_contact:
        forms.append(PersonContactForm(request.session['billing_contact']))
        forms[-1].name = _("Billing contact")
    if tech_contact:
        forms.append(PersonContactForm(request.session['tech_contact']))
        forms[-1].name = _("Technical contact")
    return render_to_response(template_name, {"forms": forms,
                                              "title": unicode(_('Organization application')) + ' - ' + unicode(_('Review'))},
                              context_instance=RequestContext(request))

@transaction.commit_manually
def organization_application_save(request):
    try:
        membership = Membership(type='O', status='N',
                                nationality=request.session['membership']['nationality'],
                                municipality=request.session['membership']['municipality'],
                                extra_info=request.session['membership']['extra_info'])
        
        organization = contact_from_dict(request.session['organization'])
        
        def get_or_none(dict, key):
            if dict.has_key(key):
                return dict[key]
            else:
                return None
        
        person = contact_from_dict(get_or_none(request.session, 'person'))
        billing_contact = contact_from_dict(get_or_none(request.session, 'billing_contact'))
        tech_contact = contact_from_dict(get_or_none(request.session, 'tech_contact'))
        
        organization.save()
        membership.organization = organization
        if person:
            person.save()
            membership.person = person
        if billing_contact:
            billing_contact.save()
            membership.billing_contact = billing_contact
        if tech_contact:
            tech_contact.save()
            membership.tech_contact = tech_contact
        
        membership.save()
        transaction.commit()
        request.session.set_expiry(0) # make this expire when the browser exits
        for i in ['membership', 'person', 'billing_contact', 'tech_contact']:
            try:
                del request.session[i]
            except:
                pass
        logging.info("New application %s from %s:." % (str(organization), request.META['REMOTE_ADDR']))
        return redirect('new_organization_application_success')
    except Exception, e:
        transaction.rollback()
        logging.error("Encountered %s" % repr(e))
        logging.error("Transaction rolled back.")
        return redirect('new_application_fail')

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


def membership_do_preapprove(request, id):
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

def membership_preapprove(request, id):
    membership_do_preapprove(request, id)
    return redirect('membership_edit', id)

def membership_preapprove_ajax(request, id):
    membership = get_object_or_404(Membership, id=id)
    if membership.status != 'N':
        return HttpResponse(id, mimetype='text/plain')
    membership_do_preapprove(request, id)
    return HttpResponse(id, mimetype='text/plain')

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

def membership_approve_many(request, id_list):
    for id in id_list:
        membership_approve(id)

def handle_json(request):
    msg = cjson.decode(request.raw_post_data)
    funcs = {'PREAPPROVE': membership_preapprove_many}
    return funcs[content['requestType']](request, msg['payload'])

def membership_json_detail(request, id):
    # A naive method of dict construction is used here. It's not very fancy,
    # but Django's serialization seems to take such a tedious route that this
    # seems simpler.
    membership = get_object_or_404(Membership, id=id)
    #sleep(1)
    
    json_obj = {}
    for attr in ['type', 'status', 'created', 'last_changed', 'municipality',
                 'nationality', 'extra_info']:
        # Get the translated value for choice fields, not database field values
        if attr in ['type', 'status']:
            attr_val = getattr(membership, 'get_' + attr + '_display')()
        else:
            attr_val = getattr(membership, attr, u'')
        
        if isinstance(attr_val, basestring):
            json_obj[attr] = attr_val
        elif isinstance(attr_val, datetime):
            json_obj[attr] = attr_val.ctime()
        else:
            json_obj[attr] = str(attr_val)
    json_obj['str'] = str(membership)
    
    contacts_json_obj = {}
    json_obj['contacts'] = contacts_json_obj
    for attr in ['person', 'billing_contact', 'tech_contact', 'organization']:
        attr_val = getattr(membership, attr, None)
        if not attr_val:
            continue
        
        contact_json_obj = {}
        for c_attr in ['first_name', 'given_names', 'last_name',
                       'organization_name', 'street_address', 'postal_code',
                       'post_office', 'country', 'phone', 'sms', 'email',
                       'homepage']:
            c_attr_val = getattr(attr_val, c_attr, u'')
            contact_json_obj[c_attr] = c_attr_val
            contacts_json_obj[attr] = contact_json_obj
    
    #return HttpResponse(simplejson.dumps(json_obj, sort_keys=True, indent=4),
    #                    mimetype='application/json')
    return HttpResponse(simplejson.dumps(json_obj, sort_keys=True, indent=4),
                        mimetype='text/plain')
