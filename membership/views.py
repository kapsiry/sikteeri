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

from models import *
from forms import MembershipForm, PersonContactForm, OrganizationContactForm
from utils import log_change

def contact_from_contact_form(f):
    f = f.cleaned_data
    c = Contact(street_address=f['street_address'],
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
            if pfx == 'organization_contact':
                f.translated_title = _("Organization's contact")
            elif pfx == 'administrative_contact':
                f.translated_title = _('Administrative contact')
            elif pfx == 'tech_contact':
                f.translated_title = _('Technical contact')
            elif pfx == 'billing_contact':
                f.translated_title = _('Billing contact')
            contact_forms.append(f)
        
        if membership_form.is_valid() and all([cf.is_valid() for cf in contact_forms]):
            mf = membership_form.cleaned_data
            contacts = {}
            for cf in contact_forms:
                contact = contact_from_contact_form(cf)
                contacts[cf.prefix] = contact
            try:
                contacts['administrative_contact'].save()
                if contacts.has_key('organization_contact'):
                    contacts['organization_contact'].save()
                membership = Membership(type=membership_type, status='N',
                                        person=contacts['administrative_contact'],
                                        nationality=mf['nationality'],
                                        municipality=mf['municipality'],
                                        extra_info=mf['extra_info'])
                
                if contacts.has_key('organization_contact'):
                    membership.organization = contacts['organization_contact']
                
                for cf in contact_forms:
                    if cf.prefix == 'administrative_contact':
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
                if contacts.has_key('organization_contact'):
                    request.session.set_expiry(0) # make this expire when the browser exits
                    request.session['new_membership_id'] = membership.id
                    logging.debug("Registered session, membership id: %i." %request.session['new_membership_id'])
                logging.info('A new membership application from %s:\n %s' % (request.META['REMOTE_ADDR'], repr(membership_form.cleaned_data)))
            except Exception, e:
                transaction.rollback()
                logging.error("Encountered %s" % repr(e))
                logging.error("Transaction rolled back while trying to save %s or one of the following contacts:" % repr(membership_form.cleaned_data))
                for cf in contact_forms:
                    logging.error("%s: %s" % (cf.prefix, repr(cf.cleaned_data)))
                return redirect('new_application_fail')
            if contacts.has_key('organization_contact'):
                return redirect('new_organization_application_success')
            else:
                return redirect('new_person_application_success')
    else:
        membership_form = MembershipForm()
        contact_forms = []
        for pfx in contact_prefixes:
            if pfx == 'organization_contact':
                f = OrganizationContactForm(prefix=pfx)
            if pfx != 'organization_contact':
                f = PersonContactForm(prefix=pfx)
            
            if pfx == 'organization_contact':
                f.translated_title = _("Organization's contact")
            elif pfx == 'administrative_contact':
                f.translated_title = _('Administrative contact')
            elif pfx == 'tech_contact':
                f.translated_title = _('Technical contact')
            elif pfx == 'billing_contact':
                f.translated_title = _('Billing contact')
            contact_forms.append(f)
    
    return render_to_response(template_name, {"membership_form": membership_form,
                                              "contact_forms": contact_forms},
                              context_instance=RequestContext(request))


@transaction.commit_manually
def new_contact_worker(request, contact_prefix, next_contact_prefix, template_name):
    if request.method == 'POST':
        if contact_prefix == 'organization_contact':
            f = OrganizationContactForm(request.POST, prefix=contact_prefix)
        else:
            f = PersonContactForm(request.POST, prefix=contact_prefix)
        
        if f.is_valid():
            f = f.cleaned_data
            contact = contact_from_contact_form(cf)
            try:
                membership = Membership.objects.get(id=request.session['new_membership_id'])
                contact.save()
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
                logging.info('Modified membership from %s:\n %s' % (request.META['REMOTE_ADDR'], repr(membership)))
            except Exception, e:
                transaction.rollback()
                logging.error("Encountered %s" % repr(e))
                logging.error("Transaction rolled back while trying to save %s or the following contact:" % repr(membership_form.cleaned_data))
                logging.error("%s: %s" % (contact_prefix, repr(f)))
                return redirect('new_contact_fail')
            return redirect('new_application_success')
    else:
        membership_form = MembershipForm()
        contact_forms = []
        for pfx in contact_prefixes:
            if pfx == 'organization_contact':
                f = OrganizationContactForm(prefix=pfx)
            if pfx != 'organization_contact':
                f = PersonContactForm(prefix=pfx)
            
            if pfx == 'organization_contact':
                f.translated_title = _("Organization's contact")
            elif pfx == 'administrative_contact':
                f.translated_title = _('Administrative contact')
            elif pfx == 'tech_contact':
                f.translated_title = _('Technical contact')
            elif pfx == 'billing_contact':
                f.translated_title = _('Billing contact')
            contact_forms.append(f)
    
    return render_to_response(template_name, {"membership_form": membership_form,
                                              "contact_forms": contact_forms},
                              context_instance=RequestContext(request))


def new_organization_application(request, template_name='membership/new_application.html'):
    return new_application_worker(request, ['organization_contact', 'administrative_contact'], template_name, 'O')
#['administrative_contact', 'billing_contact', 'tech_contact']

def new_person_application(request, template_name='membership/new_application.html'):
    return new_application_worker(request, ['administrative_contact'], template_name, 'P')

def new_application(request, template_name='membership/choose_membership_type.html'):
    return render_to_response(template_name, {})


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
