# -*- coding: utf-8 -*-

import logging

from django.conf import settings
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.template import RequestContext
from django.forms import ModelForm
from django.utils.encoding import force_unicode
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.contrib.comments.models import Comment
from django.db import transaction

from models import *
from forms import MembershipForm, ContactForm
from utils import dict_diff


def contact_from_contact_form(f):
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
    if f.has_key['organization_name']:
        c.organization_name = f['organization_name']
    return c


def new_application_worker(request, contact_prefixes, template_name, membership_type):
    if request.method == 'POST':
        membership_form = MembershipForm(request.POST)
        contact_forms = []
        for pfx in contact_prefixes:
            f = ContactForm(request.POST, prefix=pfx)
            if pfx == 'organization_contact':
                f.enable_organization_name()
            contact_forms.append(f)
        
        if membership_form.is_valid() and all([cf.is_valid() for cf in contact_forms]):
            mf = membership_form.cleaned_data
            membership = Membership(type=membership_type, status='N',
                                    municipality=f['municipality'],
                                    nationality=f['nationality'],
                                    extra_info=f['info'])
            for cf in contact_forms:
                contact = contact_from_contact_form(cf.cleaned_data)
                if c.prefix == 'person_contact':
                    membership.person = contact
                elif c.prefix == 'billing_contact':
                    membership.billing_contact = contact
                elif c.prefix == 'tech_contact':
                    membership.tech_contact = contact
                elif c.prefix == 'organization_contact':
                    membership.organization = contact
                contact.save()
            membership.save()
            transaction.commit()
            logging.info('A new membership application from %s:\n %s' % (request.META['REMOTE_ADDR'], repr(membership_form.cleaned_data)))            
            return HttpResponseRedirect('/new/success/')
    else:
        membership_form = MembershipForm()
        contact_forms = []
        for pfx in contact_prefixes:
            f = ContactForm(prefix=pfx)
            if pfx == 'organization_contact':
                f.enable_organization_name()
            contact_forms.append(f)
    
    return render_to_response(template_name, {"membership_form": membership_form,
                                              "contact_forms": contact_forms},
                              context_instance=RequestContext(request))


@transaction.commit_manually
def new_organization_application(request, template_name='membership/new_application.html'):
    return new_application_worker(request, ['organization_contact', 'person_contact',
                                            'billing_contact', 'tech_contact'], template_name,
                                  'O')
#    membership_type = forms.ChoiceField(choices=MEMBER_TYPES, label=_('membership type'))
#    status = forms.ChoiceField(choices=MEMBER_STATUS, label=_('membership status'))

@transaction.commit_manually
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
            from django.contrib.admin.models import LogEntry, CHANGE
            LogEntry.objects.log_action(
                user_id         = request.user.pk,
                content_type_id = ContentType.objects.get_for_model(membership).pk,
                object_id       = membership.pk,
                object_repr     = force_unicode(membership),
                action_flag     = CHANGE,
                change_message  = repr(dict_diff(before, after)) # XXX
            )

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
    return redirect('membership_edit', id)

def membership_preapprove_many(request, id_list):
    for id in id_list:
        membership_preapprove(id)

@login_required
def bill_list(request, template_name='membership/bill_list.html'):
    return render_to_response(template_name, {'bills': Bill.objects.all()},
                              context_instance=RequestContext(request))
@login_required
def unpaid_bill_list(request, template_name='membership/bill_list.html'):
    return render_to_response(template_name, {'bills': Bill.objects.filter(is_paid__exact=False)},
                              context_instance=RequestContext(request))


def handle_json(request):
    msg = cjson.decode(request.raw_post_data)
    funcs = {'PREAPPROVE': membership_preapprove_many}
    return funcs[content['requestType']](request, msg['payload'])
