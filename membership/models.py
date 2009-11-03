# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.template.loader import get_template
from django.template import Context

from reference_numbers import *


MEMBER_TYPES = (('P', _('Person')),
                ('O', _('Organization')))
MEMBER_STATUS = (('N', _('New')),
                 ('P', _('Pre-approved')),
                 ('A', _('Approved')),
                 ('D', _('Disabled')))

class Membership(models.Model):
    type = models.CharField(max_length=1, choices=MEMBER_TYPES)
    status = models.CharField(max_length=1, choices=MEMBER_STATUS, default='N')
    created = models.DateTimeField(auto_now_add=True)
    accepted = models.DateTimeField()
    last_changed = models.DateTimeField(auto_now=True)

    given_name = models.CharField(max_length=128, blank=True)
    first_names = models.CharField(max_length=128, blank=True)
    last_name = models.CharField(max_length=128, blank=True)
    organization_name = models.CharField(max_length=256, blank=True)

    municipality = models.CharField(_('place of residence'), max_length=128)
    nationality = models.CharField(max_length=128)

    street_address = models.CharField(max_length=128)
    postal_code = models.CharField(max_length=10)
    post_office = models.CharField(max_length=128)
    country = models.CharField(max_length=128)

    phone = models.CharField(max_length=64)
    sms = models.CharField(max_length=64)
    email = models.EmailField(blank=True)
    homepage = models.URLField(blank=True)
    info = models.TextField(blank=True)

    def __str__(self):
        if self.organization_name:
            return self.organization_name
        else:
            return u'%s %s' % (self.last_name, self.given_name)

    def accept(self):
        self.status = 'A'
        self.accepted = datetime.now()
        self.save()


class Alias(models.Model):
    owner = models.ForeignKey('Membership')
    name = models.CharField(max_length=128, unique=True)
    created = models.DateTimeField(auto_now_add=True)
    expiration_date = models.DateTimeField(blank=True)


class BillingCycle(models.Model):
    membership = models.ForeignKey('Membership')
    start =  models.DateTimeField(default=datetime.now())
    end =  models.DateTimeField()

    # XXX-paste: Why are these fields here, when they are also in the Bill class?
    is_paid = models.BooleanField(default=False)
    bill_sent = models.BooleanField(default=False)

    # XXX-paste: Do these have any significance?
    created = models.DateTimeField(auto_now_add=True)
    last_changed = models.DateTimeField(auto_now=True)

    def save(self, force_insert=False, force_update=False):
        self.end = self.start + timedelta(days=365)
        super(BillingCycle, self).save(force_insert, force_update) # Call the "real" save() method.


class Bill(models.Model):
    cycle = models.ForeignKey(BillingCycle)
    reminder_count = models.IntegerField(default=0)
    due_date = models.DateTimeField()

    is_paid = models.BooleanField(default=False)
    reference_number = models.CharField(max_length=64, unique=True) # NOT an integer since it can begin with 0 XXX: format
    sum = models.DecimalField(max_digits=6, decimal_places=2) # This limits sum to 9999,99

    created = models.DateTimeField(auto_now_add=True)
    last_changed = models.DateTimeField(auto_now=True)

    def save(self, force_insert=False, force_update=False):
        if not due_date:
            self.due_date = datetime.now() + timedelta(days=14)
        if not reference_number:
            self.reference_number = add_checknumber(self.id) # XXX: Is id available before first save?
        super(Bill, self).save(force_insert, force_update) # Call the "real" save() method.

    def render_as_text(self):
        t = get_template('membership/bill.txt')
        return t.render(Context(
            {'cycle': self.cycle, 'due_date': self.due_date, 'account': settings.BANK_ACCOUNT_NUMBER,
             'reference_number': self.reference_number, 'sum': self.sum}))

    def send_as_email(self):
        send_mail(_('Your bill for Kapsi membership'), self.render_as_text(), settings.BILLING_EMAIL_FROM,
            [self.cycle.membership.email], fail_silently=False)
        self.cycle.bill_sent = True
        self.cycle.save()


class Payment(models.Model):
    """
    Payment object for billing
    """
    bill = models.ForeignKey('Bill')
    transaction_id = models.CharField(max_length=30) # arkistointitunnus
    #XXX-paste: Again? It's in Bill. Also unique prevents double payments, which can happen IRL
    reference_number = models.CharField(max_length=64, unique=True)

    payment_day = models.DateTimeField()
    amount = models.DecimalField(max_digits=6, decimal_places=2) # This limits sum to 9999,99
    type = models.CharField(max_length=64) # tilisiirto/pano/jokumuu
    payer_name = models.CharField(max_length=64) # maksajan nimi
    message = models.CharField(max_length=64) # viesti (viestikenttä)

    created = models.DateTimeField(auto_now_add=True)
    last_changed = models.DateTimeField(auto_now=True)
