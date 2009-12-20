# -*- coding: utf-8 -*-

import logging

from django.conf import settings
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.template import RequestContext
from django.forms import ModelForm
from django.contrib.auth.decorators import login_required
from django.contrib.comments.models import Comment
from django.db import transaction
from django.http import HttpResponseRedirect

from models import *
from forms import MembershipForm, PersonContactForm, OrganizationContactForm
from utils import log_change

def contact_from_contact_form(f):
    f = f.cleaned_data
    c = Contact(first_name=f['first_name'],
                given_names=f['given_names'],
                last_name=f['last_name'],
                street_address=f['street_address'],
                postal_code=f['postal_code'],
                post_office=f['post_office'],
                country=f['country'],
                phone=f['phone'],
                sms=f['sms'],
                email=f['email'],
                homepage=f['homepage'])
    
    if f.has_key('organization_name'):
        c.organization_name = f['organization_name']
    else:
        c.first_name = f['first_name']
        c.given_names = f['given_names']
        c.last_name = f['last_name']
    return c

@transaction.commit_manually
def new_application_worker(request, contact_prefixes, template_name, membership_type):
    '''Does the heavy lifting for new application form.

    TODO: implement optional contacts for for organizations'''
    if request.method == 'POST':
        membership_form = MembershipForm(request.POST)
        contact_forms = []
        for pfx in contact_prefixes:
            if pfx == 'organization_contact':
                f = OrganizationContactForm(request.POST, prefix=pfx)
            else:
                f = PersonContactForm(request.POST, prefix=pfx)
            contact_forms.append(f)
        
        if membership_form.is_valid() and all([cf.is_valid() for cf in contact_forms]):
            mf = membership_form.cleaned_data
            contacts = {}
            for cf in contact_forms:
                contact = contact_from_contact_form(cf)
                print cf.prefix
                contacts[cf.prefix] = contact
            
            try:
                contacts['person_contact'].save()
                membership = Membership(type=membership_type, status='N',
                                        person=contacts['person_contact'],
                                        nationality=mf['nationality'],
                                        municipality=mf['municipality'],
                                        extra_info=mf['extra_info'])
                
                for cf in contact_forms:
                    if cf.prefix == 'person_contact':
                        continue
                    contact = contacts[cf.prefix]
                    if cf.prefix == 'billing_contact':
                        membership.billing_contact = contact
                        logging.debug("Added billing contact %s to %s." % (str(contact), str(membership)))
                    elif cf.prefix == 'tech_contact':
                        membership.tech_contact = contact
                        logging.debug("Added tech contact %s to %s." % (str(contact), str(membership)))
                    elif cf.prefix == 'organization_contact':
                        membership.organization = contact
                        logging.debug("Added organization contact %s to %s." % (str(contact), str(membership)))
                    contact.save()
                membership.save()
                transaction.commit()
                logging.info('A new membership application from %s:\n %s' % (request.META['REMOTE_ADDR'], repr(membership_form.cleaned_data)))
            except Exception, e:
                transaction.rollback()
                logging.error("Encountered %s" % repr(e))
                logging.error("Transaction rolled back while trying to save %s or one of the following contacts:" % repr(membership_form.cleaned_data))
                for cf in contact_forms:
                    logging.error("%s: %s" % (cf.prefix, repr(cf.cleaned_data)))
                return redirect('new_application_fail')
            return redirect('new_application_success')
    else:
        membership_form = MembershipForm()
        contact_forms = []
        for pfx in contact_prefixes:
            if pfx == 'organization_contact':
                f = OrganizationContactForm(prefix=pfx)
            else:
                f = PersonContactForm(prefix=pfx)
            contact_forms.append(f)
    
    return render_to_response(template_name, {"membership_form": membership_form,
                                              "contact_forms": contact_forms},
                              context_instance=RequestContext(request))


def new_organization_application(request, template_name='membership/new_application.html'):
    return new_application_worker(request, ['organization_contact', 'person_contact',
                                            'billing_contact', 'tech_contact'], template_name, 'O')

def new_person_application(request, template_name='membership/new_application.html'):
    return new_application_worker(request, ['person_contact'], template_name, 'P')

def new_application(request, template_name='membership/choose_membership_type.html'):
    return render_to_response(template_name, {})


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
