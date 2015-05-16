# -*- coding: utf-8 -*-

import logging
import json
from os import remove as remove_file
from os import path
from django.conf import settings
import traceback
from django.core.exceptions import ObjectDoesNotExist
from membership.models import Contact, Membership, MEMBER_TYPES_DICT, Bill,\
    BillingCycle, Payment, ApplicationPoll
from django.template.loader import render_to_string
from django.db.models.aggregates import Sum

logger = logging.getLogger("membership.views")

from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.mail import send_mail
from django.db import transaction
from django.forms import ChoiceField, ModelForm, Form, EmailField, BooleanField
from django.forms import ModelChoiceField, CharField, Textarea, HiddenInput, FileField
from django.forms.models import model_to_dict
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseServerError
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.template import RequestContext
from django.utils.translation import ugettext_lazy as _
from django.views.generic.list import ListView
from services.models import Alias, Service, ServiceType

from forms import PersonApplicationForm, OrganizationApplicationForm, PersonContactForm, ServiceForm
from utils import log_change, serializable_membership_info, admtool_membership_details, sort_objects
from utils import bake_log_entries
from public_memberlist import public_memberlist_data
from unpaid_members import unpaid_members_data

from services.views import check_alias_availability, validate_alias

from management.commands.csvbills import process_op_csv, process_procountor_csv
from decorators import trusted_host_required

from django.db.models.query_utils import Q

ENTRIES_PER_PAGE = settings.ENTRIES_PER_PAGE

# Class based views

class SortListView(ListView):
    """ListView with search query parameter"""
    search_query = ''
    sort = None
    header = ''
    disable_duplicates_header = ''

    def get_context_data(self, **kwargs):
        context = super(SortListView, self).get_context_data(**kwargs)
        context['search_query'] = self.search_query
        context['sort'] = self.sort
        context['header'] = self.header
        context['disable_duplicates_header'] = self.disable_duplicates_header
        return context


# Public access
def new_application(request, template_name='membership/choose_membership_type.html'):
    return render_to_response(template_name, {},
                              context_instance=RequestContext(request))


# Public access
def person_application(request, template_name='membership/new_person_application.html'):
    if settings.MAINTENANCE_MESSAGE != None:
        return redirect('frontpage')
    chosen_email_forward = None
    if request.method != 'POST':
        application_form = PersonApplicationForm()
    elif request.method == 'POST':
        application_form = PersonApplicationForm(request.POST)

        if not application_form.is_valid():
            try:
                chosen_email_forward = application_form.fields['email_forward'].clean(application_form.data['email_forward'])
            except:
                pass
        else:
            f = application_form.cleaned_data
            with transaction.atomic():
                # Separate a contact dict from the other fields
                contact_dict = {}
                for k, v in f.items():
                    if k not in ['nationality', 'municipality',
                                 'public_memberlist', 'email_forward',
                                 'unix_login', 'extra_info',
                                 'mysql_database', 'postgresql_database',
                                 'login_vhost', 'poll', 'poll_other',
                                 'birth_year']:
                        contact_dict[k] = v

                person = Contact(**contact_dict)
                person.save()
                membership = Membership(type='P', status='N',
                                        person=person,
                                        nationality=f['nationality'],
                                        municipality=f['municipality'],
                                        public_memberlist=f['public_memberlist'],
                                        birth_year=f['birth_year'],
                                        extra_info=f['extra_info'])
                membership.save()

                # Service handling
                services = []

                login_alias = Alias(owner=membership, name=f['unix_login'], account=True)
                login_alias.save()
                unix_account_service = Service(servicetype=ServiceType.objects.get(servicetype='UNIX account'),
                                               alias=login_alias, owner=membership, data=f['unix_login'])
                unix_account_service.save()
                services.append(unix_account_service)

                if f['email_forward'] != 'no' and f['email_forward'] != f['unix_login']:
                    forward_alias = Alias(owner=membership, name=f['email_forward'])
                    forward_alias.save()
                    forward_alias_service = Service(servicetype=ServiceType.objects.get(servicetype='Email alias'),
                                                    alias=forward_alias, owner=membership, data=f['unix_login'])
                    forward_alias_service.save()
                    services.append(forward_alias_service)

                if f['mysql_database'] == True:
                    mysql_service = Service(servicetype=ServiceType.objects.get(servicetype='MySQL database'),
                                            alias=login_alias, owner=membership, data=f['unix_login'].replace('-', '_'))
                    mysql_service.save()
                    services.append(mysql_service)
                if f['postgresql_database'] == True:
                    postgresql_service = Service(servicetype=ServiceType.objects.get(servicetype='PostgreSQL database'),
                                                 alias=login_alias, owner=membership, data=f['unix_login'])
                    postgresql_service.save()
                    services.append(postgresql_service)
                if f['login_vhost'] == True:
                    login_vhost_service = Service(servicetype=ServiceType.objects.get(servicetype='WWW vhost'),
                                                  alias=login_alias, owner=membership, data=f['unix_login'])
                    login_vhost_service.save()
                    services.append(login_vhost_service)

                logger.debug("Attempting to save with the following services: %s." % ", ".join((str(service) for service in services)))
                # End of services

                if f['poll'] is not None:
                    answer = f['poll']
                    if answer == 'other':
                        answer = '%s: %s' % (answer, f['poll_other'])
                    pollanswer = ApplicationPoll(membership=membership,
                                                 answer=answer)
                    pollanswer.save()

                logger.info("New application %s from %s:." % (str(person), request.META['REMOTE_ADDR']))
                send_mail(_('Membership application received'),
                          render_to_string('membership/application_confirmation.txt',
                                           { 'membership': membership,
                                             'membership_type': MEMBER_TYPES_DICT[membership.type],
                                             'person': membership.person,
                                             'billing_contact': membership.billing_contact,
                                             'tech_contact': membership.tech_contact,
                                             'ip': request.META['REMOTE_ADDR'],
                                             'services': services}),
                          settings.FROM_EMAIL,
                          [membership.email_to()], fail_silently=False)
                return redirect('new_person_application_success')

    return render_to_response(template_name, {"form": application_form,
                                "chosen_email_forward": chosen_email_forward,
                                "title": _("Person member application")},
                                context_instance=RequestContext(request))


# Public access
def organization_application(request, template_name='membership/new_organization_application.html'):
    if settings.MAINTENANCE_MESSAGE != None:
        return redirect('frontpage')
    if request.method == 'POST':
        form = OrganizationApplicationForm(request.POST)

        if form.is_valid():
            f = form.cleaned_data

            d = {}
            for k, v in f.items():
                if k not in ['nationality', 'municipality', 'extra_info',
                'public_memberlist', 'organization_registration_number']:
                    d[k] = v

            organization = Contact(**d)
            membership = Membership(type='O', status='N',
                                    nationality=f['nationality'],
                                    municipality=f['municipality'],
                                    extra_info=f['extra_info'],
                                    organization_registration_number=f['organization_registration_number'],
                                    public_memberlist=f['public_memberlist'])

            request.session.set_expiry(0) # make this expire when the browser exits
            request.session['membership'] = model_to_dict(membership)

            organization_dict = model_to_dict(organization)
            request.session['organization'] = organization_dict
            return redirect('organization_application_add_contact', 'billing_contact')
    else:
        form = OrganizationApplicationForm()
    return render_to_response(template_name, {"form": form,
                                              "title": _('Organization application')},
                              context_instance=RequestContext(request))

# Public access
def organization_application_add_contact(request, contact_type,
                                         template_name='membership/new_organization_application_add_contact.html'):
    forms = ['billing_contact', 'tech_contact']
    if contact_type not in forms:
        return HttpResponseForbidden("Access denied")

    if contact_type == 'billing_contact':
        type_text = unicode(_('Billing contact'))
    elif contact_type == 'tech_contact':
        type_text = unicode(_('Technical contact'))

    if request.method == 'POST':
        form = PersonContactForm(request.POST)

        if (form.is_valid() or                 # contact is actually filled
            len(form.changed_data) == 0 or     # form is empty
            form.changed_data == ['country']): # only the country field is filled (this comes from form defaults)

            if form.is_valid():
                f = form.cleaned_data
                contact = Contact(**f)
                contact_dict = model_to_dict(contact)
                request.session[contact_type] = contact_dict
            else:
                request.session[contact_type] = None

            next_idx = forms.index(contact_type) + 1
            if next_idx == len(forms):
                return redirect('organization_application_services')
            return redirect('organization_application_add_contact', forms[next_idx])
    else:
        if request.session.has_key(contact_type):
            form = PersonContactForm(request.session[contact_type])
        else:
            form = PersonContactForm()
    return render_to_response(template_name, {"form": form, "contact_type": type_text,
                                              "step_number": forms.index(contact_type) + 2,
                                              "title": _('Organization application') + ' - ' + type_text},
                              context_instance=RequestContext(request))

# Public access
def organization_application_services(request, template_name='membership/new_organization_application_services.html'):
    if request.session.has_key('services'):
        form = ServiceForm({'mysql_database': request.session.get('mysql', ''),
                            'postgresql_database': request.session.get('postgresql', ''),
                            'login_vhost': request.session.get('login_vhost', ''),
                            'unix_login': request.session.get('unix_login', '')})
    else:
        form = ServiceForm()

    if request.method == 'POST':
        form = ServiceForm(request.POST)
        if form.is_valid():
            f = form.cleaned_data

            services = {'unix_login': f['unix_login']}

            if f['mysql_database'] != False:
                services['mysql_database'] = f['unix_login']
            elif services.has_key('mysql_database'):
                del services['mysql_database']
            if f['postgresql_database'] != False:
                services['postgresql_database'] = f['unix_login']
            elif services.has_key('postgresql'):
                del services['postgresql']
            if f['login_vhost'] != False:
                services['login_vhost'] = f['unix_login']
            elif services.has_key('login_vhost'):
                del services['login_vhost']

            request.session['services'] = services
            return redirect('organization_application_review')
        else:
            if request.session.has_key('services'):
                del request.session['services']

    return render_to_response(template_name, {"form": form,
                                              "title": unicode(_('Choose services'))},
                              context_instance=RequestContext(request))

# Public access
def organization_application_review(request, template_name='membership/new_organization_application_review.html'):
    membership = Membership(type='O', status='N',
                            nationality=request.session['membership']['nationality'],
                            municipality=request.session['membership']['municipality'],
                            extra_info=request.session['membership']['extra_info'])
    organization = Contact(**request.session.get('organization'))

    try:
        billing_contact = Contact(**request.session['billing_contact'])
    except:
        billing_contact = None

    try:
        tech_contact = Contact(**request.session['tech_contact'])
    except:
        tech_contact = None

    forms = []
    combo_dict = request.session['membership']
    for k, v in request.session['organization'].items():
        combo_dict[k] = v
    forms.append(OrganizationApplicationForm(combo_dict))
    if billing_contact:
        forms.append(PersonContactForm(request.session['billing_contact']))
        forms[-1].name = _("Billing contact")
    if tech_contact:
        forms.append(PersonContactForm(request.session['tech_contact']))
        forms[-1].name = _("Technical contact")
    return render_to_response(template_name, {"forms": forms, "services": request.session['services'],
                                              "title": unicode(_('Organization application')) + ' - ' + unicode(_('Review'))},
                              context_instance=RequestContext(request))


# Public access
def organization_application_save(request):
    with transaction.atomic():
        membership = Membership(type='O', status='N',
                                nationality=request.session['membership']['nationality'],
                                municipality=request.session['membership']['municipality'],
                                extra_info=request.session['membership']['extra_info'],
                                organization_registration_number=request.session['membership']['organization_registration_number'])

        organization = Contact(**request.session['organization'])

        try:
            billing_contact = Contact(**request.session['billing_contact'])
        except ObjectDoesNotExist:
            billing_contact = None

        try:
            tech_contact = Contact(**request.session['tech_contact'])
        except ObjectDoesNotExist:
            tech_contact = None

        organization.save()
        membership.organization = organization
        if billing_contact:
            billing_contact.save()
            membership.billing_contact = billing_contact
        if tech_contact:
            tech_contact.save()
            membership.tech_contact = tech_contact

        membership.save()

        services = []
        session = request.session
        login_alias = Alias(owner=membership, name=session['services']['unix_login'], account=True)
        login_alias.save()
        unix_account_service = Service(servicetype=ServiceType.objects.get(servicetype='UNIX account'),
                                       alias=login_alias, owner=membership, data=session['services']['unix_login'])
        unix_account_service.save()
        services.append(unix_account_service)
        if session['services'].has_key('mysql_database'):
            mysql_service = Service(servicetype=ServiceType.objects.get(servicetype='MySQL database'),
                                    alias=login_alias, owner=membership,
                                    data=session['services']['mysql_database'].replace('-', '_'))
            mysql_service.save()
            services.append(mysql_service)
        if session['services'].has_key('postgresql_database'):
            postgresql_service = Service(servicetype=ServiceType.objects.get(servicetype='PostgreSQL database'),
                                         alias=login_alias, owner=membership,
                                         data=session['services']['postgresql_database'])
            postgresql_service.save()
            services.append(postgresql_service)
        if session['services'].has_key('login_vhost'):
            login_vhost_service = Service(servicetype=ServiceType.objects.get(servicetype='WWW vhost'),
                                          alias=login_alias, owner=membership,
                                          data=session['services']['login_vhost'])
            login_vhost_service.save()
            services.append(login_vhost_service)

        send_mail(_('Membership application received'),
                  render_to_string('membership/application_confirmation.txt',
                                   { 'membership': membership,
                                     'membership_type': MEMBER_TYPES_DICT[membership.type],
                                     'organization': membership.organization,
                                     'billing_contact': membership.billing_contact,
                                     'tech_contact': membership.tech_contact,
                                     'ip': request.META['REMOTE_ADDR'],
                                     'services': services}),
                  settings.FROM_EMAIL,
                  [membership.email_to()], fail_silently=False)

        logger.info("New application %s from %s:." % (unicode(organization), request.META['REMOTE_ADDR']))
        request.session.set_expiry(0) # make this expire when the browser exits
        for i in ['membership', 'billing_contact', 'tech_contact', 'services']:
            if i in request.session:
                del request.session[i]
        return redirect('new_organization_application_success')


@permission_required('membership.edit_members')
def contact_add(request, contact_type, memberid, template_name='membership/entity_edit.html'):
    membership = get_object_or_404(Membership, id=memberid)
    forms = ['billing_contact', 'tech_contact']

    class Form(ModelForm):
        class Meta:
            model = Contact

    if contact_type not in forms:
        return HttpResponseForbidden("Access denied")

    if contact_type == 'billing_contact' and membership.billing_contact:
        return redirect('contact_edit',membership.billing_contact.id)
    elif contact_type == 'tech_contact' and membership.tech_contact:
        return redirect('contact_edit',membership.tech_contact.id)

    if request.method == 'POST':
        form = Form(request.POST)
        if form.is_valid():
            contact = Contact(**form.cleaned_data)
            contact.save()
            if contact_type == 'billing_contact':
                membership.billing_contact = contact
            elif contact_type == 'tech_contact':
                membership.tech_contact = contact
            membership.save()
            messages.success(request,
                             unicode(_("Added contact %s.") %
                             contact))
            return redirect('contact_edit', contact.id)
        else:
            messages.error(request,
                           unicode(_("New contact not saved.")))
    else:
        form = Form()
    return render_to_response(template_name,
                             {"form": form, 'memberid': memberid},
                             context_instance=RequestContext(request))

@permission_required('membership.read_members')
def contact_edit(request, id, template_name='membership/entity_edit.html'):
    contact = get_object_or_404(Contact, id=id)
    # XXX: I hate this. Wasn't there a shortcut for creating a form from instance?
    class Form(ModelForm):
        class Meta:
            model = Contact

    before = model_to_dict(contact)  # Otherwise save() (or valid?) will change the dict, needs to be here
    if request.method == 'POST':
        if not request.user.has_perm('membership.manage_members'):
            messages.error(request, unicode(_("You are not authorized to modify memberships.")))
            return redirect('contact_edit', id)

        form = Form(request.POST, instance=contact)

        if form.is_valid():
            form.save()
            after = model_to_dict(contact)
            log_change(contact, request.user, before, after)
            messages.success(request, unicode(_("Changes to contact %s saved.") % contact))
            return redirect('contact_edit', id) # form stays as POST otherwise if someone refreshes
        else:
            messages.error(request, unicode(_("Changes to contact %s not saved.") % contact))
    else:
        form =  Form(instance=contact)
        message = ""
    logentries = bake_log_entries(contact.logs.all())
    return render_to_response(template_name, {'form': form, 'contact': contact,
        'logentries': logentries, 'memberid': contact.find_memberid()},
        context_instance=RequestContext(request))

@permission_required('membership.manage_bills')
def bill_edit(request, id, template_name='membership/entity_edit.html'):
    bill = get_object_or_404(Bill, id=id)

    class Form(ModelForm):
        class Meta:
            model = Bill
            exclude = ('billingcycle', 'reminder_count', 'pdf_file')

        def __init__(self, *args, **kwargs):
            super(Form, self).__init__(*args, **kwargs)
            instance = getattr(self, 'instance', None)
            if instance and instance.pk:
                self.fields['type'].widget.attrs['readonly'] = True

        def clean_type(self):
            instance = getattr(self, 'instance', None)
            if instance and instance.pk:
                return instance.type
            else:
                return self.cleaned_data['type']

    before = model_to_dict(bill) # Otherwise save() (or valid?) will change the dict, needs to be here
    if request.method == 'POST':
        form = Form(request.POST, instance=bill)
        if form.is_valid():
            form.save()
            after = model_to_dict(bill)
            log_change(bill, request.user, before, after)
            messages.success(request, unicode(_("Changes to bill %s saved.") % bill))
            return redirect('bill_edit', id) # form stays as POST otherwise if someone refreshes
        else:
            messages.error(request, unicode(_("Changes to bill %s not saved.") % bill))
    else:
        form =  Form(instance=bill)
    logentries = bake_log_entries(bill.logs.all())
    return render_to_response(template_name, {'form': form, 'bill': bill,
        'logentries': logentries,'memberid': bill.billingcycle.membership.id},
        context_instance=RequestContext(request))

@permission_required('membership.read_bills')
def bill_pdf(request, bill_id):
    output_messages = []

    bill = get_object_or_404(Bill, id=bill_id)
    try:
        pdf = bill.generate_pdf()
        if pdf:
            response = HttpResponse(pdf, content_type='application/pdf')
            response['Content-Disposition'] = 'inline; filename=bill_%s.pdf' % bill.id
            return response
    except Exception as e:
        logger.exception("Failed to generate pdf for bill %s" % bill.id)
    response = HttpResponseServerError("Failed to generate pdf", content_type='plain/text', )
    return response

@permission_required('membership.manage_bills')
def billingcycle_connect_payment(request, id, template_name='membership/billingcycle_connect_payment.html'):
    billingcycle = get_object_or_404(BillingCycle, id=id)

    class SpeciallyLabeledModelChoiceField(ModelChoiceField):
        def label_from_instance(self, obj):
            return u"%s, %s, %s, %s" % (obj.payer_name, obj.reference_number, obj.amount, obj.payment_day)

    class PaymentForm(Form):
        qs = Payment.objects.filter(billingcycle__exact=None, ignore=False).order_by("payer_name")
        payment = SpeciallyLabeledModelChoiceField(queryset=qs,
                                                   empty_label=_("None chosen"), required=True)


    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            f = form.cleaned_data
            payment = f['payment']
            before = model_to_dict(payment)
            oldcycle = payment.billingcycle
            if oldcycle:
                oldcycle_before = model_to_dict(oldcycle)
                payment.detach_from_cycle(user=request.user)
                oldcycle_after = model_to_dict(oldcycle)
                log_change(oldcycle, request.user, oldcycle_before, oldcycle_after)

            newcycle = billingcycle
            newcycle_before = model_to_dict(newcycle)
            payment.attach_to_cycle(newcycle)
            newcycle_after = model_to_dict(newcycle)
            after = model_to_dict(payment)
            log_change(payment, request.user, before, after)
            log_change(newcycle, request.user, newcycle_before, newcycle_after)
            messages.success(request, unicode(_("Changes to payment %s saved.") % payment))
            return redirect('billingcycle_edit', id)
        else:
            messages.error(request, unicode(_("Changes to BillingCycle %s not saved.") % billingcycle))
    else:
        form =  PaymentForm()
    logentries = bake_log_entries(billingcycle.logs.all())
    return render_to_response(template_name, {'form': form, 'cycle': billingcycle,
                                              'logentries': logentries},
                              context_instance=RequestContext(request))

@permission_required('membership.can_import_payments')
def import_payments(request, template_name='membership/import_payments.html'):
    import_messages = []
    class PaymentCSVForm(Form):
        csv = FileField(label=_('CSV File'),
                         help_text=_('Choose CSV file to upload'))
        format = ChoiceField(choices=(('op', 'Osuuspankki'), ('procountor', 'Procountor')),
                           help_text=_("File type"))

    if request.method == 'POST':
        form = PaymentCSVForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                in_memory_file = request.FILES['csv']
                logger.info("Beginning payment import.")
                if form.cleaned_data['format'] == 'op':
                    import_messages = process_op_csv(in_memory_file, user=request.user)
                elif form.cleaned_data['format'] == 'procountor':
                    import_messages = process_procountor_csv(in_memory_file, user=request.user)
                messages.success(request, unicode(_("Payment import succeeded!")))
            except:
                  logger.error("%s" % traceback.format_exc())
                  logger.error("Payment CSV import failed.")
                  messages.error(request, unicode(_("Payment import failed.")))
        else:
            messages.error(request, unicode(_("Payment import failed.")))
    else:
        form = PaymentCSVForm()

    return render_to_response(template_name, {'title': _("Import payments"),
                                              'form': form,
                                              'import_messages': import_messages},
                              context_instance=RequestContext(request))

@permission_required('membership.read_bills')
def print_reminders(request, **kwargs):
    output_messages = []
    if request.method == 'POST':
        try:
            if 'marksent' in request.POST:
                for billing_cycle in BillingCycle.get_reminder_billingcycles().all():
                    bill = Bill(billingcycle=billing_cycle, type='P')
                    bill.reminder_count = billing_cycle.bill_set.count()
                    bill.save()
                    bill.generate_pdf()
                output_messages.append(_('Reminders marked as sent'))
            else:
                pdf = BillingCycle.get_pdf_reminders()
                if pdf:
                    response = HttpResponse(pdf, content_type='application/pdf')
                    response['Content-Disposition'] = 'attachment; filename=reminders.pdf'
                    return response
                else:
                    output_messages.append(_('Error processing PDF'))
        except RuntimeError:
            output_messages.append(_('Error processing PDF'))
        except IOError:
            output_messages.append(_('Cannot open PDF file'))
    return render_to_response('membership/print_reminders.html',
    {'title': _("Print paper reminders"),
     'output_messages': output_messages,
     'count': BillingCycle.get_reminder_billingcycles().count()},
     context_instance=RequestContext(request))

@permission_required('membership.manage_bills')
def billingcycle_edit(request, id, template_name='membership/entity_edit.html'):
    cycle = get_object_or_404(BillingCycle, id=id)

    class Form(ModelForm):
        is_paid_forced = False
        class Meta:
            model = BillingCycle
            exclude = ('membership', 'start', 'end', 'sum', 'reference_number')

        def disable_fields(self):
            self.fields['is_paid'].required = False
            if cycle.amount_paid() >= cycle.sum and cycle.is_paid:
                self.fields['is_paid'].widget.attrs['readonly'] = 'readonly'
                self.is_paid_forced = True

        def clean_is_paid(self):
            if self.is_paid_forced:
                return cycle.is_paid
            else:
                return self.cleaned_data['is_paid']

    before = model_to_dict(cycle) # Otherwise save() (or valid?) will change the dict, needs to be here
    if request.method == 'POST':
        form = Form(request.POST, instance=cycle)
        form.disable_fields()
        if form.is_valid():
            form.save()
            after = model_to_dict(cycle)
            log_change(cycle, request.user, before, after)
            messages.success(request, unicode(_("Changes to billing cycle %s saved.") % cycle))
            return redirect('billingcycle_edit', id) # form stays as POST otherwise if someone refreshes
        else:
            messages.error(request, unicode(_("Changes to bill %s not saved.") % cycle))
    else:
        form =  Form(instance=cycle)
        form.disable_fields()
    logentries = bake_log_entries(cycle.logs.all())
    return render_to_response(template_name,
                              {'form': form, 'cycle': cycle,
                               'logentries': logentries,
                               'memberid': cycle.membership.id},
        context_instance=RequestContext(request))

@permission_required('membership.manage_bills')
def payment_edit(request, id, template_name='membership/entity_edit.html'):
    payment = get_object_or_404(Payment, id=id)

    class SpeciallyLabeledModelChoiceField(ModelChoiceField):
        def label_from_instance(self, obj):
            return u"%s, %s" % (obj.membership, unicode(obj))

    class Form(ModelForm):
        class Meta:
            model = Payment
            #exclude = ('billingcycle')

        billingcycle = CharField(widget=HiddenInput(), required=False)
        #billingcycle = CharField(required=False)
        message = CharField(widget=Textarea(attrs={'rows': 5, 'cols': 60}))

        def disable_fields(self):
            if payment.billingcycle:
                self.fields['ignore'].required = False
                self.fields['ignore'].widget.attrs['readonly'] = 'readonly'
            self.fields['billingcycle'].required = False
            self.fields['billingcycle'].widget.attrs['readonly'] = 'readonly'
            self.fields['reference_number'].required = False
            self.fields['reference_number'].widget.attrs['readonly'] = 'readonly'
            self.fields['message'].required = False
            self.fields['message'].widget.attrs['readonly'] = 'readonly'
            self.fields['transaction_id'].required = False
            self.fields['transaction_id'].widget.attrs['readonly'] = 'readonly'
            self.fields['payment_day'].required = False
            self.fields['payment_day'].widget.attrs['readonly'] = 'readonly'
            self.fields['amount'].required = False
            self.fields['amount'].widget.attrs['readonly'] = 'readonly'
            self.fields['type'].required = False
            self.fields['type'].widget.attrs['readonly'] = 'readonly'
            self.fields['payer_name'].required = False
            self.fields['payer_name'].widget.attrs['readonly'] = 'readonly'
            self.fields['comment'].required = False

        def clean_ignore(self):
            if payment.billingcycle:
                return False
            else:
                return self.cleaned_data['ignore']
        def clean_billingcycle(self):
            return payment.billingcycle
        def clean_reference_number(self):
            return payment.reference_number
        def clean_message(self):
            return payment.message
        def clean_transaction_id(self):
            return payment.transaction_id
        def clean_payment_day(self):
            return payment.payment_day
        def clean_amount(self):
            return payment.amount
        def clean_type(self):
            return payment.type
        def clean_payer_name(self):
            return payment.payer_name

    before = model_to_dict(payment) # Otherwise save() (or valid?) will change the dict, needs to be here
    oldcycle = payment.billingcycle
    if request.method == 'POST':
        form = Form(request.POST, instance=payment)
        form.disable_fields()
        if form.is_valid():
            form.save()
            newcycle = payment.billingcycle
            if oldcycle != newcycle:
                if oldcycle:
                    oldcycle.update_is_paid()
            if newcycle:
              newcycle.update_is_paid()
            after = model_to_dict(payment)
            log_change(payment, request.user, before, after)
            messages.success(request, unicode(_("Changes to payment %s saved.") % payment))
            return redirect('payment_edit', id) # form stays as POST otherwise if someone refreshes
        else:
            messages.error(request, unicode(_("Changes to payment %s not saved.") % payment))
            return redirect('payment_edit', id) # form clears otherwise, this is a borderline acceptable hack
    else:
        form = Form(instance=payment)
        form.disable_fields()

    logentries = bake_log_entries(payment.logs.all())
    if payment.billingcycle:
            memberid = payment.billingcycle.membership.id
    else:
            memberid = None

    return render_to_response(template_name, {'form': form, 'payment': payment,
        'logentries': logentries, 'memberid': memberid},
        context_instance=RequestContext(request))

@permission_required('membership.manage_bills')
def send_duplicate_notification(request, payment, **kwargs):
    payment = get_object_or_404(Payment, id=payment)
    payment.send_duplicate_payment_notice(request.user)
    return redirect('payment_edit', payment.id)

@permission_required('membership.read_members')
def membership_edit(request, id, template_name='membership/membership_edit.html'):
    membership = get_object_or_404(Membership, id=id)

    class Form(ModelForm):
        class Meta:
            model = Membership
            exclude = ('person', 'billing_contact', 'tech_contact', 'organization')

        def clean_status(self):
            return membership.status
        def clean_approved(self):
            return membership.approved

        def disable_fields(self):
            self.fields['status'].required = False
            self.fields['status'].widget.attrs['disabled'] = 'disabled'
            self.fields['status'].widget.attrs['readonly'] = 'readonly'
            self.fields['approved'].required = False
            self.fields['approved'].widget.attrs['readonly'] = 'readonly'
            instance = getattr(self, 'instance', None)
            if instance and instance.type == 'O':
                self.fields["birth_year"].widget = HiddenInput()
                self.fields['birth_year'].required = False

    if request.method == 'POST':
        if not request.user.has_perm('membership.manage_members'):
            return HttpResponseForbidden(_("Permission manage required"))
        form = Form(request.POST, instance=membership)
        before = model_to_dict(membership)
        form.disable_fields()
        if form.is_valid():
            form.save()
            after = model_to_dict(membership)
            log_change(membership, request.user, before, after)
            return redirect('membership_edit', id) # form stays as POST otherwise if someone refreshes
    else:
        form = Form(instance=membership)
        form.disable_fields()
    # Pretty print log entries for template
    logentries = bake_log_entries(membership.logs.all())
    return render_to_response(template_name, {'form': form,
        'membership': membership, 'logentries': logentries},
        context_instance=RequestContext(request))

@permission_required('membership.read_members')
def membership_duplicates(request, id):
    membership = get_object_or_404(Membership, id=id)

    view_params = {'queryset': membership.duplicates(),
                   'template_name': 'membership/membership_list.html',
                   'context_object_name': 'member_list',
                   'header':  _(u"List duplicates for member #%(mid)i %(membership)s" % {"mid":membership.id,
                                                                               "membership":unicode(membership)}),
                   'disable_duplicates_header': True,
                   'paginate_by': ENTRIES_PER_PAGE}

    return member_object_list(request, **view_params)

@permission_required('membership.read_members')
def unpaid_paper_reminded(request):
    view_params = {'queryset': Membership.paper_reminder_sent_unpaid_after(),
                   'template_name': 'membership/membership_list.html',
                   'context_object_name': 'member_list',
                   'paginate_by': ENTRIES_PER_PAGE
                   }

    return member_object_list(request, **view_params)

@permission_required('membership.read_members')
def unpaid_paper_reminded_plain(request):
    view_params = {'queryset': Membership.paper_reminder_sent_unpaid_after().order_by('id'),
                   'template_name': 'membership/membership_list_plaintext.html',
                   'context_object_name': 'member_list'
                   }

    return member_object_list(request, **view_params)


@permission_required('membership.delete_members')
def membership_delete(request, id, template_name='membership/membership_delete.html'):
    membership = get_object_or_404(Membership, id=id)
    class ConfirmForm(Form):
        confirm = BooleanField(label=_('To confirm deletion, you must check this box:'),
                               required=True)

    if request.method == 'POST':
        form = ConfirmForm(request.POST)
        if form.is_valid():
            f = form.cleaned_data
            membership_str = unicode(membership)
            membership.delete_membership(request.user)
            messages.success(request, unicode(_('Member %s successfully deleted.') % membership_str))
            logger.info("User %s deleted member %s." % (request.user.username, membership))
            return redirect('membership_edit', membership.id)
    else:
        form = ConfirmForm()

    return render_to_response(template_name,
                              {'form': form,
                               'membership': membership },
                              context_instance=RequestContext(request))

@permission_required('membership.dissociate_members')
def membership_dissociate(request, id, template_name='membership/membership_dissociate.html'):
    membership = get_object_or_404(Membership, id=id)
    class ConfirmForm(Form):
        confirm = BooleanField(label=_('To confirm dissociation, you must check this box:'),
                               required=True)

    if request.method == 'POST':
        form = ConfirmForm(request.POST)
        if form.is_valid():
            f = form.cleaned_data
            membership_str = unicode(membership)
            membership.dissociate(request.user)
            messages.success(request, unicode(_('Member %s successfully dissociated.') % membership_str))
            logger.info("User %s dissociated member %s." % (request.user.username, membership))
            return redirect('membership_edit', membership.id)
    else:
        form = ConfirmForm()

    return render_to_response(template_name,
                              {'form': form,
                               'membership': membership },
                              context_instance=RequestContext(request))

@permission_required('membership.request_dissociation_for_member')
def membership_request_dissociation(request, id, template_name='membership/membership_request_dissociation.html'):
    membership = get_object_or_404(Membership, id=id)
    class ConfirmForm(Form):
        confirm = BooleanField(label=_('To confirm state change, you must check this box:'),
                               required=True)

    if request.method == 'POST':
        form = ConfirmForm(request.POST)
        if form.is_valid():
            f = form.cleaned_data
            membership_str = unicode(membership)
            membership.request_dissociation(request.user)
            messages.success(request, unicode(_('Member %s successfully transferred to requested dissociation state.') % membership_str))
            logger.info("User %s requested dissociation for member %s." % (request.user.username, membership))
            return redirect('membership_edit', membership.id)
    else:
        form = ConfirmForm()

    return render_to_response(template_name,
                              {'form': form,
                               'membership': membership },
                              context_instance=RequestContext(request))

@permission_required('membership.request_dissociation_for_member')
def membership_cancel_dissociation_request(request, id, template_name='membership/membership_cancel_dissociation_request.html'):
    membership = get_object_or_404(Membership, id=id)
    class ConfirmForm(Form):
        confirm = BooleanField(label=_('To confirm state change, you must check this box:'),
                               required=True)

    if request.method == 'POST':
        form = ConfirmForm(request.POST)
        if form.is_valid():
            f = form.cleaned_data
            membership_str = unicode(membership)
            membership.cancel_dissociation_request(request.user)
            messages.success(request, unicode(_('Member %s successfully transferred back to approved state.') % membership_str))
            logger.info("User %s requested dissociation for member %s." % (request.user.username, membership))
            return redirect('membership_edit', membership.id)
    else:
        form = ConfirmForm()

    return render_to_response(template_name,
                              {'form': form,
                               'membership': membership },
                              context_instance=RequestContext(request))

@permission_required('membership.manage_members')
def membership_convert_to_organization(request, id, template_name='membership/membership_convert_to_organization.html'):
    membership = get_object_or_404(Membership, id=id)
    class ConfirmForm(Form):
        confirm = BooleanField(label=_('To confirm conversion, you must check this box:'),
                               required=True)

    if request.method == 'POST':
        form = ConfirmForm(request.POST)
        if form.is_valid():
            f = form.cleaned_data
            membership.type = 'O'
            contact = membership.person
            membership.person = None
            membership.organization = contact
            membership.save()
            log_change(membership, request.user, change_message="Converted to an organization")
            messages.success(request, unicode(_('Member %s successfully converted to an organization.') % membership))
            logger.info("User %s converted member %s to an organization." % (request.user.username, membership))
            return redirect('membership_edit', membership.id)
    else:
        form = ConfirmForm()

    return render_to_response(template_name,
                              {'form': form,
                               'membership': membership },
                              context_instance=RequestContext(request))

@permission_required('membership.manage_members')
def membership_preapprove_json(request, id):
    get_object_or_404(Membership, id=id).preapprove(request.user)
    return HttpResponse(id, content_type='text/plain')

@permission_required('membership.manage_members')
def membership_approve_json(request, id):
    get_object_or_404(Membership, id=id).approve(request.user)
    return HttpResponse(id, content_type='text/plain')

@permission_required('membership.read_members')
def membership_detail_json(request, id):
    membership = get_object_or_404(Membership, id=id)
    #sleep(1)
    json_obj = serializable_membership_info(membership)
    return HttpResponse(json.dumps(json_obj, sort_keys=True, indent=4),
                        content_type='application/json')
    # return HttpResponse(json.dumps(json_obj, sort_keys=True, indent=4),
    #                     content_type='text/plain')

# Public access
def handle_json(request):
    logger.debug("RAW POST DATA: %s" % request.body)
    msg = json.loads(request.body)
    funcs = {'PREAPPROVE': membership_preapprove_json,
             'APPROVE': membership_approve_json,
             'MEMBERSHIP_DETAIL': membership_detail_json,
             'ALIAS_AVAILABLE': check_alias_availability,
             'VALIDATE_ALIAS': validate_alias}
    if not funcs.has_key(msg['requestType']):
        raise NotImplementedError()
    logger.debug("AJAX call %s, payload: %s" % (msg['requestType'],
                                                 unicode(msg['payload'])))
    try:
        return funcs[msg['requestType']](request, msg['payload'])
    except Exception as e:
        logger.critical("%s" % traceback.format_exc())
        raise e

@login_required
def test_email(request, template_name='membership/test_email.html'):
    class RecipientForm(Form):
        recipient = EmailField(label=_('Recipient e-mail address'))

    if request.method == 'POST':
        form = RecipientForm(request.POST)
        if form.is_valid():
            f = form.cleaned_data
        else:
            return render_to_response(template_name, {'form': form},
                                      context_instance=RequestContext(request))

        body = render_to_string('membership/test_email.txt', { "user": request.user })
        send_mail(u"Testisähköposti", body,
                  settings.FROM_EMAIL,
#                  request.user.email,
                  [f["recipient"]], fail_silently=False)
        logger.info("Sent a test e-mail to %s" % f["recipient"])

    return render_to_response(template_name, {'form': RecipientForm()},
                              context_instance=RequestContext(request))

@trusted_host_required
def membership_metrics(request):
    unpaid_cycles = BillingCycle.objects.filter(is_paid=False)
    unpaid_sum = unpaid_cycles.aggregate(Sum("sum"))['sum__sum']
    if unpaid_sum == None:
        unpaid_sum = "0.0"
    d = {'memberships':
         {'new': Membership.objects.filter(status='N').count(),
          'preapproved': Membership.objects.filter(status='P').count(),
          'approved': Membership.objects.filter(status='A').count(),
          'deleted': Membership.objects.filter(status='D').count(),
          },
         'bills':
         {'unpaid_count': unpaid_cycles.count(),
          'unpaid_sum': float(unpaid_sum),
          },
         }
    return HttpResponse(json.dumps(d, sort_keys=True, indent=4),
                        content_type='application/json')

@trusted_host_required
def public_memberlist(request):
    template_name = 'membership/public_memberlist.xml'
    data = public_memberlist_data()
    return render_to_response(template_name, data, content_type='text/xml')

@trusted_host_required
def unpaid_members(request):
    json_obj = unpaid_members_data()
    return HttpResponse(json.dumps(json_obj, sort_keys=True, indent=4),
                        content_type='application/json')

@trusted_host_required
def admtool_membership_detail_json(request, id):
    membership = get_object_or_404(Membership, id=id)
    json_obj = admtool_membership_details(membership)
    return HttpResponse(json.dumps(json_obj, sort_keys=True, indent=4),
                        content_type='application/json')

@trusted_host_required
def admtool_lookup_alias_json(request, alias):
    aliases = Alias.objects.filter(name__iexact=alias)
    if len(aliases) == 1:
        return HttpResponse(aliases[0].owner.id, content_type='text/plain')
    elif not aliases:
        return HttpResponse("No match", content_type='text/plain')
    return HttpResponse("Too many matches", content_type='text/plain')



@permission_required('membership.read_members')
def member_object_list(request, **kwargs):
    kwargs = sort_objects(request,**kwargs)
    return SortListView.as_view(**kwargs)(request)

@permission_required('membership.read_bills')
def billing_object_list(request, **kwargs):
    kwargs = sort_objects(request,**kwargs)
    return SortListView.as_view(**kwargs)(request)

# This should list any bills/cycles that were forcefully set as paid even
# though insufficient payments were paid.
# @permission_required('membership.read_bills')
# def forced_paid_cycles_list(*args, **kwargs):
#     paid_q = Q(is_paid__exact=True)
#     payments_sum_q = Q(payment_set.aggregate(Sum('amount'))__lt=sum)
#     qs = BillingCycle.objects.filter(paid_q, payments_sum_q)
#     return ListView.as_view(**kwargs, queryset=qs)(request))


@permission_required('membership.read_members')
def search(request, **kwargs):
    query = request.GET.get('query', '')

    # Shorthand for viewing a membership by giving # and the id
    if query.startswith("#"):
        try:
            return redirect('membership_edit', int(query.lstrip("#")))
        except ValueError as ve:
            pass

    qs = Membership.search(query)

    if qs.count() == 1:
        return redirect('membership_edit', qs[0].id)

    kwargs['queryset'] = qs.order_by("organization__organization_name",
                     "person__last_name",
                     "person__first_name")
    kwargs['search_query'] = query
    kwargs = sort_objects(request,**kwargs)
    return SortListView.as_view(**kwargs)(request)
