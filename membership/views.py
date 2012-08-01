# -*- coding: utf-8 -*-

import logging
import json
from sikteeri import settings
from membership.models import Contact, Membership, MEMBER_TYPES_DICT, Bill,\
    BillingCycle, Payment
from django.template.loader import render_to_string
import traceback
from django.db.models.aggregates import Sum
logger = logging.getLogger("membership.views")

from django.core.mail import send_mail
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.template import RequestContext
from django.forms import ModelForm, Form, EmailField, BooleanField, ModelChoiceField, CharField, Textarea, HiddenInput, FileField
from django.contrib.auth.decorators import login_required, permission_required
from django.db import transaction
from django.utils.translation import ugettext_lazy as _
from django.http import HttpResponse, HttpResponseForbidden
from django.contrib import messages

from services.models import Alias, Service, ServiceType

from forms import PersonApplicationForm, OrganizationApplicationForm, PersonContactForm, LoginField, ServiceForm
from utils import log_change, serializable_membership_info, admtool_membership_details, sort_objects
from utils import bake_log_entries
from public_memberlist import public_memberlist_data
from unpaid_members import unpaid_members_data

from services.views import check_alias_availability, validate_alias

from management.commands.csvbills import process_csv as payment_csv_import
from decorators import trusted_host_required

from django.db.models.query_utils import Q
import django.views.generic.list_detail
from sikteeri.settings import ENTRIES_PER_PAGE

# Public access
def new_application(request, template_name='membership/choose_membership_type.html'):
    return render_to_response(template_name, {},
                              context_instance=RequestContext(request))

# Public access
@transaction.commit_manually
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
            try:
                # Separate a contact dict from the other fields
                contact_dict = {}
                for k, v in f.items():
                    if k not in ['nationality', 'municipality',
                                 'public_memberlist', 'email_forward',
                                 'unix_login', 'extra_info',
                                 'mysql_database', 'postgresql_database',
                                 'login_vhost']:
                        contact_dict[k] = v

                person = Contact(**contact_dict)
                person.save()
                membership = Membership(type='P', status='N',
                                        person=person,
                                        nationality=f['nationality'],
                                        municipality=f['municipality'],
                                        public_memberlist=f['public_memberlist'],
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
                transaction.commit()
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
            except Exception, e:
                transaction.rollback()
                logger.critical("%s" % traceback.format_exc())
                logger.critical("Transaction rolled back while trying to process %s." % repr(application_form.cleaned_data))
                return redirect('new_application_error')

    with transaction.autocommit():
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
                if k not in ['nationality', 'municipality', 'extra_info', 'public_memberlist']:
                    d[k] = v

            organization = Contact(**d)
            membership = Membership(type='O', status='N',
                                    nationality=f['nationality'],
                                    municipality=f['municipality'],
                                    extra_info=f['extra_info'],
                                    public_memberlist=f['public_memberlist'])

            request.session.set_expiry(0) # make this expire when the browser exits
            request.session['membership'] = membership.__dict__.copy()
            organization_dict = organization.__dict__.copy()
            del organization_dict['_state']
            request.session['organization'] = organization_dict
            return redirect('organization_application_add_contact', 'billing_contact')
    else:
        form = OrganizationApplicationForm()
    return render_to_response(template_name, {"form": form,
                                              "title": _('Organization application')},
                              context_instance=RequestContext(request))

# Public access
def organization_application_add_contact(request, contact_type, template_name='membership/new_organization_application_add_contact.html'):
    forms = ['billing_contact', 'tech_contact']
    if contact_type not in forms:
        return HttpResponseForbidden("Access denied")

    if contact_type == 'billing_contact':
        type_text = 'Billing contact'
    elif contact_type == 'tech_contact':
        type_text = 'Technical contact'

    if request.method == 'POST':
        form = PersonContactForm(request.POST)
        if form.is_valid() or len(form.changed_data) == 0:
            if form.is_valid():
                f = form.cleaned_data
                contact = Contact(**f)
                contact_dict = contact.__dict__.copy()
                del contact_dict['_state']
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
@transaction.commit_manually
def organization_application_save(request):
    try:
        membership = Membership(type='O', status='N',
                                nationality=request.session['membership']['nationality'],
                                municipality=request.session['membership']['municipality'],
                                extra_info=request.session['membership']['extra_info'])

        organization = Contact(**request.session['organization'])

        try:
            billing_contact = Contact(**request.session['billing_contact'])
        except:
            billing_contact = None

        try:
            tech_contact = Contact(**request.session['tech_contact'])
        except:
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

        transaction.commit()

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
            try:
                del request.session[i]
            except:
                pass
        return redirect('new_organization_application_success')
    except Exception, e:
        transaction.rollback()
        logger.error("%s" % traceback.format_exc())
        logger.error("Transaction rolled back.")
        return redirect('new_application_error')

@permission_required('membership.read_members')
def contact_edit(request, id, template_name='membership/entity_edit.html'):
    contact = get_object_or_404(Contact, id=id)
    # XXX: I hate this. Wasn't there a shortcut for creating a form from instance?
    class Form(ModelForm):
        class Meta:
            model = Contact

    before = contact.__dict__.copy() # Otherwise save() (or valid?) will change the dict, needs to be here
    if request.method == 'POST':
        if not request.user.has_perm('membership.manage_members'):
            messages.error(request, unicode(_("You are not authorized to modify memberships.")))
            return redirect('contact_edit', id)

        form = Form(request.POST, instance=contact)

        if form.is_valid():
            form.save()
            after = contact.__dict__
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
            exclude = ('billingcycle', 'reminder_count')

    before = bill.__dict__.copy() # Otherwise save() (or valid?) will change the dict, needs to be here
    if request.method == 'POST':
        form = Form(request.POST, instance=bill)
        if form.is_valid():
            form.save()
            after = bill.__dict__
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
            before = payment.__dict__.copy()
            oldcycle = payment.billingcycle
            if oldcycle:
                oldcycle_before = oldcycle.__dict__.copy()
                payment.detach_from_cycle()
                oldcycle_after = oldcycle.__dict__.copy()
                log_change(oldcycle, request.user, oldcycle_before, oldcycle_after)

            newcycle = billingcycle
            newcycle_before = newcycle.__dict__.copy()
            payment.attach_to_cycle(newcycle)
            newcycle_after = newcycle.__dict__.copy()
            after = payment.__dict__
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

    if request.method == 'POST':
        form = PaymentCSVForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                in_memory_file = request.FILES['csv']
                logger.info("Beginning payment import.")
                import_messages = payment_csv_import(in_memory_file)
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

    before = cycle.__dict__.copy() # Otherwise save() (or valid?) will change the dict, needs to be here
    if request.method == 'POST':
        form = Form(request.POST, instance=cycle)
        form.disable_fields()
        if form.is_valid():
            form.save()
            after = cycle.__dict__
            log_change(cycle, request.user, before, after)
            messages.success(request, unicode(_("Changes to billing cycle %s saved.") % cycle))
            return redirect('billingcycle_edit', id) # form stays as POST otherwise if someone refreshes
        else:
            messages.error(request, unicode(_("Changes to bill %s not saved.") % cycle))
    else:
        form =  Form(instance=cycle)
        form.disable_fields()
    logentries = bake_log_entries(cycle.logs.all())
    return render_to_response(template_name, {'form': form, 'cycle': cycle,
        'logentries': logentries,'memberid': cycle.membership.id},
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

    before = payment.__dict__.copy() # Otherwise save() (or valid?) will change the dict, needs to be here
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
            after = payment.__dict__
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
            self.fields['status'].widget.attrs['readonly'] = 'readonly'
            self.fields['approved'].required = False
            self.fields['approved'].widget.attrs['readonly'] = 'readonly'

    if request.method == 'POST':
        if not request.user.has_perm('membership.manage_members'):
            return HttpResponseForbidden(_("Permission manage required"))
        form = Form(request.POST, instance=membership)
        before = membership.__dict__.copy()
        form.disable_fields()
        if form.is_valid():
            form.save()
            after = membership.__dict__
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
                   'template_object_name': 'member',
                   'extra_context': {'header':
                                     _(u"List duplicates for member #%i %s" % (membership.id,
                                                                               unicode(membership))),
                                     'disable_duplicates_header': True},
                   'paginate_by': ENTRIES_PER_PAGE}

    return member_object_list(request, **view_params)

@permission_required('membership.delete_members')
@transaction.commit_on_success
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

@permission_required('membership.manage_members')
@transaction.commit_on_success
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
@transaction.commit_on_success
def membership_preapprove_json(request, id):
    get_object_or_404(Membership, id=id).preapprove(request.user)
    return HttpResponse(id, mimetype='text/plain')

@permission_required('membership.manage_members')
@transaction.commit_on_success
def membership_approve_json(request, id):
    get_object_or_404(Membership, id=id).approve(request.user)
    return HttpResponse(id, mimetype='text/plain')

@permission_required('membership.read_members')
def membership_detail_json(request, id):
    membership = get_object_or_404(Membership, id=id)
    #sleep(1)
    json_obj = serializable_membership_info(membership)
    return HttpResponse(json.dumps(json_obj, sort_keys=True, indent=4),
                        mimetype='application/json')
    # return HttpResponse(json.dumps(json_obj, sort_keys=True, indent=4),
    #                     mimetype='text/plain')

# Public access
def handle_json(request):
    logger.debug("RAW POST DATA: %s" % request.raw_post_data)
    msg = json.loads(request.raw_post_data)
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
    except Exception, e:
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
                        mimetype='application/json')

@trusted_host_required
def public_memberlist(request):
    template_name = 'membership/public_memberlist.xml'
    data = public_memberlist_data()
    return render_to_response(template_name, data, mimetype='text/xml')

@trusted_host_required
def unpaid_members(request):
    json_obj = unpaid_members_data()
    return HttpResponse(json.dumps(json_obj, sort_keys=True, indent=4),
                        mimetype='application/json')

@trusted_host_required
def admtool_membership_detail_json(request, id):
    membership = get_object_or_404(Membership, id=id)
    json_obj = admtool_membership_details(membership)
    return HttpResponse(json.dumps(json_obj, sort_keys=True, indent=4),
                        mimetype='application/json')

@trusted_host_required
def admtool_lookup_alias_json(request, alias):
    aliases = Alias.objects.filter(name__iexact=alias)
    if len(aliases) == 1:
        return HttpResponse(aliases[0].owner.id, mimetype='text/plain')
    elif not aliases:
        return HttpResponse("No match", mimetype='text/plain')
    return HttpResponse("Too many matches", mimetype='text/plain')



@permission_required('membership.read_members')
def member_object_list(request, **kwargs):
    kwargs = sort_objects(request,**kwargs)
    return django.views.generic.list_detail.object_list(request, **kwargs)

@permission_required('membership.read_bills')
def billing_object_list(request, **kwargs):
    kwargs = sort_objects(request,**kwargs)
    return django.views.generic.list_detail.object_list(request, **kwargs)

# This should list any bills/cycles that were forcefully set as paid even
# though insufficient payments were paid.
# @permission_required('membership.read_bills')
# def forced_paid_cycles_list(*args, **kwargs):
#     paid_q = Q(is_paid__exact=True)
#     payments_sum_q = Q(payment_set.aggregate(Sum('amount'))__lt=sum)
#     qs = BillingCycle.objects.filter(paid_q, payments_sum_q)
#     return django.views.generic.list_detail.object_list(request, queryset=qs, *args, **kwargs)

@permission_required('membership.read_members')
def search(request, **kwargs):
    try:
        query = kwargs['query']
        del kwargs['query']
        if not query:
            raise KeyError()
    except KeyError, ke:
        query = request.REQUEST.get("query", None)
        extra = kwargs.get('extra_context', {})
        extra['search_query'] = query
        kwargs['extra_context'] = extra

    # Shorthand for viewing a membership by giving # and the id
    if query.startswith("#"):
        try:
            return redirect('membership_edit', int(query.lstrip("#")))
        except ValueError, ve:
            pass

    qs = Membership.search(query)

    if qs.count() == 1:
        return redirect('membership_edit', qs[0].id)

    kwargs['queryset'] = qs.order_by("organization__organization_name",
                     "person__last_name",
                     "person__first_name")
    kwargs = sort_objects(request,**kwargs)
    return django.views.generic.list_detail.object_list(request, **kwargs)
