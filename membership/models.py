# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import logging

from django.db import models
from django.db.models import Q, F
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.template.loader import render_to_string
from django.template import Context
from django.core.mail import send_mail

from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.generic import GenericRelation

from reference_numbers import generate_membership_bill_reference_number
from reference_numbers import generate_checknumber, add_checknumber

class BillingEmailNotFound(Exception): pass
class MembershipFlowError(Exception): pass

MEMBER_TYPES = (('P', _('Person')),
                ('S', _('Supporting')),
                ('O', _('Organization')),
                ('H', _('Honorary')))
MEMBER_STATUS = (('N', _('New')),
                 ('P', _('Pre-approved')),
                 ('A', _('Approved')),
                 ('D', _('Disabled')))

def logging_log_change(sender, instance, created, **kwargs):
    operation = "created" if created else "modified"
    logging.info('%s %s: %s' % (sender, operation, repr(instance)))

class Contact(models.Model):
    logs = GenericRelation(LogEntry)
    last_changed = models.DateTimeField(auto_now=True, verbose_name=_('contact changed'))
    created = models.DateTimeField(auto_now_add=True, verbose_name=_('contact created'))

    first_name = models.CharField(max_length=128, verbose_name=_('First name'), blank=True) # Primary first name
    given_names = models.CharField(max_length=128, verbose_name=_('Given names'), blank=True)
    last_name = models.CharField(max_length=128, verbose_name=_('Last name'), blank=True)
    organization_name = models.CharField(max_length=256, verbose_name=_('Organization name'), blank=True)

    street_address = models.CharField(max_length=128, verbose_name=_('Street address'))
    postal_code = models.CharField(max_length=10, verbose_name=_('Postal code'))
    post_office = models.CharField(max_length=128, verbose_name=_('Post office'))
    country = models.CharField(max_length=128, verbose_name=_('Country'))
    phone = models.CharField(max_length=64, verbose_name=_('Phone'))
    sms = models.CharField(max_length=64, blank=True, verbose_name=_('SMS number'))
    email = models.EmailField(blank=True, verbose_name=_('E-mail'))
    homepage = models.URLField(blank=True, verbose_name=_('Homepage'))

    def save(self, *args, **kwargs):
        if self.organization_name:
            if len(self.organization_name) < 5:
                raise Exception("Organization's name should be at least 5 characters.")
        super(Contact, self).save(*args, **kwargs)

    def __unicode__(self):
        if self.organization_name:
            return self.organization_name
        else:
            return u'%s %s' % (self.last_name, self.first_name)


class Membership(models.Model):
    logs = GenericRelation(LogEntry)

    type = models.CharField(max_length=1, choices=MEMBER_TYPES, verbose_name=_('Membership type'))
    status = models.CharField(max_length=1, choices=MEMBER_STATUS, default='N', verbose_name=_('Membership status'))
    created = models.DateTimeField(auto_now_add=True, verbose_name=_('Membership created'))
    accepted = models.DateTimeField(blank=True, null=True, verbose_name=_('Membership accepted'))
    last_changed = models.DateTimeField(auto_now=True, verbose_name=_('Membership changed'))

    municipality = models.CharField(_('Home municipality'), max_length=128)
    nationality = models.CharField(_('Nationality'), max_length=128)

    person = models.ForeignKey('Contact', related_name='person_set', verbose_name=_('Person'), blank=True, null=True)
    billing_contact = models.ForeignKey('Contact', related_name='billing_set', verbose_name=_('Billing contact'), blank=True, null=True)
    tech_contact = models.ForeignKey('Contact', related_name='tech_contact_set', verbose_name=_('Technical contact'), blank=True, null=True)
    organization = models.ForeignKey('Contact', related_name='organization_set', verbose_name=_('Organization'), blank=True, null=True)

    extra_info = models.TextField(blank=True, verbose_name=_('Additional information'))

    def email(self):
        if self.organization:
            return self.organization.email
        else:
            return self.person.email

    def get_billing_contact(self):
        '''Resolves the actual billing contact. Useful for billing details.'''
        if self.billing_contact:
            return self.billing_contact
        elif self.person:
            return self.person
        else:
            return self.organization

    def billing_email(self):
        '''Finds the best email address for billing'''
        contact_priority_list = [self.billing_contact, self.person,
            self.organization]
        for contact in contact_priority_list:
            if contact:
                if contact.email:
                    return unicode(contact.email)
        raise BillingEmailNotFound("Neither billing or administrative contact "+
            "has an email address")

    def save(self, *args, **kwargs):
        if self.person and self.organization:
            raise Exception("Person-contact and organization-contact are mutually exclusive.")
        if not self.person and not self.organization:
            raise Exception("Either Person-contact or organization-contact must be defined.")
        super(Membership, self).save(*args, **kwargs)

    def preapprove(self):
        if self.status != 'N':
            raise MembershipOperationError("A membership from other state than preapproved can't be approved.")
        self.status = 'P'
        self.save()

    def approve(self):
        if self.status != 'P':
            raise MembershipOperationError("A membership from other state than preapproved can't be approved.")
        self.status = 'A'
        self.save()

    def __repr__(self):
        return "<Membership(%s): %s (%i)>" % (self.type, str(self), self.id)

    def __str__(self):
        return unicode(self).encode('ASCII', 'backslashreplace')
    def __unicode__(self):
        if self.organization:
            return self.organization.__unicode__()
        else:
            return self.person.__unicode__()


class Alias(models.Model):
    owner = models.ForeignKey('Membership', verbose_name=_('Alias owner'))
    name = models.CharField(max_length=128, unique=True, verbose_name=_('Alias name'))
    account = models.BooleanField(default=False, verbose_name=_('Is UNIX account'))
    created = models.DateTimeField(auto_now_add=True, verbose_name=_('Created'))
    comment = models.CharField(max_length=128, blank=True, verbose_name=_('Comment'))
    expiration_date = models.DateTimeField(blank=True, null=True, verbose_name=_('Alias expiration date'))


class Fee(models.Model):
    type = models.CharField(max_length=1, choices=MEMBER_TYPES, verbose_name=_('Fee type'))
    start = models.DateTimeField(_('Valid from date'))
    sum = models.DecimalField(_('Sum'), max_digits=6, decimal_places=2)

    def __unicode__(self):
        return "Fee for %s, %s euros, %s--" % (self.get_type_display(), str(self.sum), str(self.start))

class BillingCycle(models.Model):
    membership = models.ForeignKey('Membership', verbose_name=_('Membership'))
    start =  models.DateTimeField(default=datetime.now(), verbose_name=_('Start'))
    end =  models.DateTimeField(verbose_name=_('End'))
    sum = models.DecimalField(_('Sum'), max_digits=6, decimal_places=2) # This limits sum to 9999,99
    is_paid = models.BooleanField(default=False, verbose_name=_('Is paid'))
    reference_number = models.CharField(max_length=64, verbose_name=_('Reference number')) # NOT an integer since it can begin with 0 XXX: format

    def last_bill(self):
        try:
            return Bill.objects.filter(billingcycle=self).order_by('-due_date')[0]
        except IndexError, ie:
            return None

    def is_last_bill_late(self):
        if self.is_paid or self.last_bill() == None:
            return False
        if datetime.now() > self.last_bill().due_date:
            return True
        return False

    def get_fee(self):
        for_this_type = Q(type=self.membership.type)
        not_before_start = Q(start__lte=self.start)
        fees = Fee.objects.filter(for_this_type, not_before_start)
        valid_fee = fees.latest('start').sum
        return valid_fee

    def __unicode__(self):
        return str(self.start) + "--" + str(self.end)

    def save(self, *args, **kwargs):
        if not self.end:
            self.end = self.start + timedelta(days=365)
        if not self.reference_number:
            self.reference_number = generate_membership_bill_reference_number(self.membership.id, self.start.year)
        if not self.sum:
            self.sum = self.get_fee()
        super(BillingCycle, self).save(*args, **kwargs)

class Bill(models.Model):
    billingcycle = models.ForeignKey(BillingCycle, verbose_name=_('Cycle'))
    reminder_count = models.IntegerField(default=0, verbose_name=_('Reminder count'))
    due_date = models.DateTimeField(verbose_name=_('Due date'))

    created = models.DateTimeField(auto_now_add=True, verbose_name=_('Created'))
    last_changed = models.DateTimeField(auto_now=True, verbose_name=_('Last changed'))

    def is_due(self):
        return self.due_date < datetime.now()

    def __unicode__(self):
        return _('Sent on') + ' ' + str(self.created)

    def save(self, *args, **kwargs):
        if not self.due_date:
            self.due_date = datetime.now() + timedelta(days=14) # FIXME: Hardcoded
        super(Bill, self).save(*args, **kwargs)

    def is_reminder(self):
        cycle = self.billingcycle
        bills = cycle.bill_set.order_by('due_date')
        if self.id != bills[0].id:
            return True
        return False

    # FIXME: different template based on class? should this code be here?
    def render_as_text(self):
        membership = self.billingcycle.membership
        return render_to_string('membership/bill.txt', {
            'bill_id': self.id,
            'member_id': membership.id,
            'billing_name': unicode(membership.get_billing_contact()),
            'street_address': membership.get_billing_contact().street_address,
            'postal_code': membership.get_billing_contact().postal_code,
            'post_office': membership.get_billing_contact().post_office,
            'billingcycle': self.billingcycle,
            'iban_account_number': settings.IBAN_ACCOUNT_NUMBER,
            'bic_code': settings.BIC_CODE,
            'due_date': self.due_date,
            'reference_number': self.billingcycle.reference_number,
            'sum': self.billingcycle.sum
            })

    # FIXME: Should save sending date
    def send_as_email(self):
        membership = self.billingcycle.membership
        if self.billingcycle.sum > 0:
            send_mail(settings.BILL_SUBJECT, self.render_as_text(),
                settings.BILLING_FROM_EMAIL,
                [membership.billing_email()], fail_silently=False)
            logging.info('A bill sent as email to %s: %s' % (membership.email,
                repr(Bill)))
        else:
            logging.info('Bill not sent: membership fee zero for %s: %s' % (
                membership.email, repr(Bill)))
        self.billingcycle.bill_sent = True
        self.billingcycle.save()


class Payment(models.Model):
    """
    Payment object for billing
    """
    # While Payment refers to Bill, someone might send a payment that has a reference
    # number, which does not correspond to any Bills...
    bill = models.ForeignKey('Bill', verbose_name=_('Bill'), null=True)

    reference_number = models.CharField(max_length=64, verbose_name=_('Reference number'), blank=True) # Not unique, because people can send multiple payments
    message = models.CharField(max_length=64, verbose_name=_('Message'), blank=True) # viesti (viestikenttä)
    transaction_id = models.CharField(max_length=30, verbose_name=_('Transaction id')) # arkistointitunnus
    payment_day = models.DateTimeField(verbose_name=_('Payment day'))
    amount = models.DecimalField(max_digits=6, decimal_places=2, verbose_name=_('Amount')) # This limits sum to 9999,99
    type = models.CharField(max_length=64, verbose_name=_('Type')) # tilisiirto/pano/jokumuu
    payer_name = models.CharField(max_length=64, verbose_name=_('Payer name')) # maksajan nimi

    def __unicode__(self):
        return '%.2f euros (reference %s)' % (self.amount, self.reference_number)

models.signals.post_save.connect(logging_log_change, sender=Membership)
models.signals.post_save.connect(logging_log_change, sender=Contact)
models.signals.post_save.connect(logging_log_change, sender=Alias)
models.signals.post_save.connect(logging_log_change, sender=BillingCycle)
models.signals.post_save.connect(logging_log_change, sender=Bill)
models.signals.post_save.connect(logging_log_change, sender=Payment)
