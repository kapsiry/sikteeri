# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import logging

from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.template.loader import get_template
from django.template import Context
from django.core.mail import send_mail

from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.generic import GenericRelation

from reference_numbers import *


MEMBER_TYPES = (('P', _('Person')),
                ('O', _('Organization')))
MEMBER_STATUS = (('N', _('New')),
                 ('P', _('Pre-approved')),
                 ('A', _('Approved')),
                 ('D', _('Disabled')))

def log_change(sender, instance, created, **kwargs):
    operation = "created" if created else "modified"
    logging.info('%s %s: %s' % (sender, operation, repr(instance)))


class Membership(models.Model):
    logs = GenericRelation(LogEntry)

    type = models.CharField(max_length=1, choices=MEMBER_TYPES, verbose_name=_('membership type'))
    status = models.CharField(max_length=1, choices=MEMBER_STATUS, default='N', verbose_name=_('membership status'))
    created = models.DateTimeField(auto_now_add=True, verbose_name=_('membership created'))
    accepted = models.DateTimeField(blank=True, null=True, verbose_name=_('membership accepted'))
    last_changed = models.DateTimeField(auto_now=True, verbose_name=_('membership changed'))

    given_name = models.CharField(max_length=128, blank=True, verbose_name=_('given name'))
    first_names = models.CharField(max_length=128, blank=True, verbose_name=_('first names'))
    last_name = models.CharField(max_length=128, blank=True, verbose_name=_('last name'))
    organization_name = models.CharField(max_length=256, blank=True, verbose_name=_('organization name'))

    municipality = models.CharField(_('place of residence'), max_length=128,)
    nationality = models.CharField(max_length=128, verbose_name=_('nationality'))

    street_address = models.CharField(max_length=128, verbose_name=_('street address'))
    postal_code = models.CharField(max_length=10, verbose_name=_('postal code'))
    post_office = models.CharField(max_length=128, verbose_name=_('post office'))
    country = models.CharField(max_length=128, verbose_name=_('country'))

    phone = models.CharField(max_length=64, verbose_name=_('phone'))
    sms = models.CharField(max_length=64, blank=True, verbose_name=_('sms'))
    email = models.EmailField(blank=True, verbose_name=_('email'))
    homepage = models.URLField(blank=True, verbose_name=_('homepage'))
    info = models.TextField(blank=True, verbose_name=_('info'))

    def __unicode__(self):
        if self.organization_name:
            return self.organization_name
        else:
            return u'%s %s' % (self.last_name, self.given_name)

    def accept(self):
        self.status = 'A'
        self.accepted = datetime.now()
        self.save()


class Alias(models.Model):
    owner = models.ForeignKey('Membership', verbose_name=_('alias owner'))
    name = models.CharField(max_length=128, unique=True, verbose_name=_('alias name'))
    created = models.DateTimeField(auto_now_add=True, verbose_name=_('created'))
    expiration_date = models.DateTimeField(blank=True, verbose_name=_('alias expiration date'))


class BillingCycle(models.Model):
    membership = models.ForeignKey('Membership', verbose_name=_('membership'))
    start =  models.DateTimeField(default=datetime.now(), verbose_name=_('start'))
    end =  models.DateTimeField(verbose_name=_('end'))

    # XXX-paste: Why are these fields here, when they are also in the Bill class?
    is_paid = models.BooleanField(default=False, verbose_name=_('is paid'))
    bill_sent = models.BooleanField(default=False, verbose_name=_('bill sent'))

    # XXX-paste: Do these have any significance?
    created = models.DateTimeField(auto_now_add=True, verbose_name=_('created'))
    last_changed = models.DateTimeField(auto_now=True, verbose_name=_('last changed'))

    def __unicode__(self):
        return str(self.start) + "--" + str(self.end)

    def save(self, force_insert=False, force_update=False):
        self.end = self.start + timedelta(days=365)
        super(BillingCycle, self).save(force_insert, force_update) # Call the "real" save() method.


class Bill(models.Model):
    cycle = models.ForeignKey(BillingCycle, verbose_name=_('cycle'))
    reminder_count = models.IntegerField(default=0, verbose_name=_('reminder count'))
    due_date = models.DateTimeField(verbose_name=_('due date'))

    is_paid = models.BooleanField(default=False, verbose_name=_('is paid'))
    reference_number = models.CharField(max_length=64, unique=True, verbose_name=_('reference number')) # NOT an integer since it can begin with 0 XXX: format
    sum = models.DecimalField(max_digits=6, decimal_places=2, verbose_name=_('sum')) # This limits sum to 9999,99

    created = models.DateTimeField(auto_now_add=True, verbose_name=_('created'))
    last_changed = models.DateTimeField(auto_now=True, verbose_name=_('last changed'))

    def __unicode__(self):
        return 'Sent on ' + str(self.created)

    def save(self, force_insert=False, force_update=False):
        if not self.due_date:
            self.due_date = datetime.now() + timedelta(days=14)
        if not self.reference_number:
            # ID is not available before first save, so we look for the previous one
            # XXX There is a better way in Postgres, but is there a portable way?
            last = Bill.objects.order_by('id')[:1]
            if not last:
                number = 0
            else:
                number = last[0].id + 1
            self.reference_number = add_checknumber(str(number))
        if not self.sum:
            self.sum = settings.MEMBERSHIP_FEE
        super(Bill, self).save(force_insert, force_update) # Call the "real" save() method.

    def render_as_text(self): # XXX: Use django.template.loader.render_to_string
        t = get_template('membership/bill.txt')
        return t.render(Context(
            {'cycle': self.cycle, 'due_date': self.due_date, 'account': settings.BANK_ACCOUNT_NUMBER,
             'reference_number': self.reference_number, 'sum': self.sum}))

    # XXX: Should save sending date
    def send_as_email(self):
        send_mail(_('Your bill for Kapsi membership'), self.render_as_text(), settings.BILLING_EMAIL_FROM,
            [self.cycle.membership.email], fail_silently=False)
        logging.info('A Bill sent as email to %s: %s' % (self.cycle.membership.email, repr(Bill)))
        self.cycle.bill_sent = True
        self.cycle.save()


class Payment(models.Model):
    """
    Payment object for billing
    """
    bill = models.ForeignKey('Bill', verbose_name=_('bill'))
    transaction_id = models.CharField(max_length=30, verbose_name=_('transaction id')) # arkistointitunnus
    #XXX-paste: Again? It's in Bill. Also unique prevents double payments, which can happen IRL
    reference_number = models.CharField(max_length=64, unique=True, verbose_name=_('reference number'))

    payment_day = models.DateTimeField(verbose_name=_('payment day'))
    amount = models.DecimalField(max_digits=6, decimal_places=2, verbose_name=_('amount')) # This limits sum to 9999,99
    type = models.CharField(max_length=64, verbose_name=_('type')) # tilisiirto/pano/jokumuu
    payer_name = models.CharField(max_length=64, verbose_name=_('payer name')) # maksajan nimi
    message = models.CharField(max_length=64, verbose_name=_('message')) # viesti (viestikenttä)

    created = models.DateTimeField(auto_now_add=True, verbose_name=_('created'))
    last_changed = models.DateTimeField(auto_now=True, verbose_name=_('last changed'))

models.signals.post_save.connect(log_change, sender=Membership)
models.signals.post_save.connect(log_change, sender=Alias)
models.signals.post_save.connect(log_change, sender=BillingCycle)
models.signals.post_save.connect(log_change, sender=Bill)
models.signals.post_save.connect(log_change, sender=Payment)
