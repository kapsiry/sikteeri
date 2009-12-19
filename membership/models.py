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
                ('S', _('Supporting')),
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

    calling_name = models.CharField(max_length=128, blank=True) # Primary first name or organization name
    municipality = models.CharField(_('place of residence'), max_length=128)
    nationality = models.CharField(max_length=128)

    billing_first_names = models.CharField(max_length=128, verbose_name=_('given name'))
    billing_last_name = models.CharField(max_length=128, verbose_name=_('first names'))
    billing_street_address = models.CharField(max_length=128, verbose_name=_('last name'))
    billing_postal_code = models.CharField(max_length=10, verbose_name=_('organization name'))
    billing_post_office = models.CharField(max_length=128, verbose_name=_('post office'))
    billing_country = models.CharField(max_length=128, verbose_name=_('country'))
    billing_phone = models.CharField(max_length=64, verbose_name=_('phone'))
    billing_sms = models.CharField(max_length=64, blank=True, verbose_name=_('sms'))
    billing_email = models.EmailField(blank=True, verbose_name=_('email'))

    contact_first_names = models.CharField(max_length=128, blank=True)
    contact_last_name = models.CharField(max_length=128, blank=True)
    contact_street_address = models.CharField(max_length=128, blank=True)
    contact_postal_code = models.CharField(max_length=10, blank=True)
    contact_post_office = models.CharField(max_length=128, blank=True)
    contact_country = models.CharField(max_length=128, blank=True)
    contact_phone = models.CharField(max_length=64, blank=True)
    contact_sms = models.CharField(max_length=64, blank=True)
    contact_email = models.EmailField(blank=True)

    homepage = models.URLField(blank=True, verbose_name=_('homepage'))
    extra_info = models.TextField(blank=True, verbose_name=_('info'))

    def email(self):
        if self.contact_email:
            return self.contact_email
        elif self.billing_email:
            return self.billing_email

    def __unicode__(self):
        if self.type == 'O':
            return self.calling_name
        else:
            return u'%s, %s' % (self.billing_last_name, self.calling_name)

    def accept(self):
        self.status = 'A'
        self.accepted = datetime.now()
        self.save()


class Alias(models.Model):
    owner = models.ForeignKey('Membership', verbose_name=_('alias owner'))
    name = models.CharField(max_length=128, unique=True, verbose_name=_('alias name'))
    created = models.DateTimeField(auto_now_add=True, verbose_name=_('created'))
    expiration_date = models.DateTimeField(blank=True, verbose_name=_('alias expiration date'))


class Fee(models.Model):
    type = models.CharField(max_length=1, choices=MEMBER_TYPES)
    start = models.DateTimeField()
    sum = models.DecimalField(max_digits=6, decimal_places=2)

    def __unicode__(self):
        return "Fee for %s, %s euros, %s--" % (self.get_type_display(), str(self.sum), str(self.start))

class BillingCycle(models.Model):
    membership = models.ForeignKey('Membership', verbose_name=_('membership'))
    start =  models.DateTimeField(default=datetime.now(), verbose_name=_('start'))
    end =  models.DateTimeField(verbose_name=_('end'))

    sum = models.DecimalField(max_digits=6, decimal_places=2) # This limits sum to 9999,99

    def __unicode__(self):
        return str(self.start) + "--" + str(self.end)

    def save(self, force_insert=False, force_update=False):
        if not self.end:
            self.end = self.start + timedelta(days=365)
        if not self.sum:
            self.sum = Fee.objects.filter(type__exact=self.membership.type).filter(start__lte=datetime.now()).order_by('-start')[0].sum
        super(BillingCycle, self).save(force_insert, force_update) # Call the "real" save() method.


class Bill(models.Model):
    cycle = models.ForeignKey(BillingCycle, verbose_name=_('cycle'))
    reminder_count = models.IntegerField(default=0, verbose_name=_('reminder count'))
    due_date = models.DateTimeField(verbose_name=_('due date'))

    is_paid = models.BooleanField(default=False, verbose_name=_('is paid'))
    reference_number = models.CharField(max_length=64, unique=True, verbose_name=_('reference number')) # NOT an integer since it can begin with 0 XXX: format

    created = models.DateTimeField(auto_now_add=True, verbose_name=_('created'))
    last_changed = models.DateTimeField(auto_now=True, verbose_name=_('last changed'))

    def __unicode__(self):
        return 'Sent on ' + str(self.created)

    def save(self, force_insert=False, force_update=False):
        if not self.due_date:
            self.due_date = datetime.now() + timedelta(days=14) # XXX Hardcoded
        if not self.reference_number:
            self.reference_number = add_checknumber('1337' + str(self.cycle.membership.id))
        super(Bill, self).save(force_insert, force_update) # Call the "real" save() method.

    def render_as_text(self): # XXX: Use django.template.loader.render_to_string
        t = get_template('membership/bill.txt')
        return t.render(Context(
            {'cycle': self.cycle, 'due_date': self.due_date, 'account': settings.BANK_ACCOUNT_NUMBER,
             'reference_number': self.reference_number, 'sum': self.cycle.sum}))

    # XXX: Should save sending date
    def send_as_email(self):
        send_mail(_('Your bill for Kapsi membership'), self.render_as_text(), settings.BILLING_EMAIL_FROM,
            [self.cycle.membership.billing_email], fail_silently=False)
        logging.info('A Bill sent as email to %s: %s' % (self.cycle.membership.email, repr(Bill)))
        self.cycle.bill_sent = True
        self.cycle.save()


class Payment(models.Model):
    """
    Payment object for billing
    """
    # While Payment refers to Bill, someone might send a payment that has a reference
    # number, which does not correspond to any Bills...
    bill = models.ForeignKey('Bill', verbose_name=_('bill'))

    # Not unique, because people can send multiple payments
    reference_number = models.CharField(max_length=64, unique=True, verbose_name=_('reference number'))

    transaction_id = models.CharField(max_length=30, verbose_name=_('transaction id')) # arkistointitunnus
    payment_day = models.DateTimeField(verbose_name=_('payment day'))
    amount = models.DecimalField(max_digits=6, decimal_places=2, verbose_name=_('amount')) # This limits sum to 9999,99
    type = models.CharField(max_length=64, verbose_name=_('type')) # tilisiirto/pano/jokumuu
    payer_name = models.CharField(max_length=64, verbose_name=_('payer name')) # maksajan nimi
    message = models.CharField(max_length=64, verbose_name=_('message')) # viesti (viestikenttä)


models.signals.post_save.connect(log_change, sender=Membership)
models.signals.post_save.connect(log_change, sender=Alias)
models.signals.post_save.connect(log_change, sender=BillingCycle)
models.signals.post_save.connect(log_change, sender=Bill)
models.signals.post_save.connect(log_change, sender=Payment)
