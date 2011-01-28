# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
import logging
logger = logging.getLogger("models")

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Q, F
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.template.loader import render_to_string
from django.template import Context
from django.core.mail import send_mail

from django.contrib.admin.models import LogEntry
from django.contrib.contenttypes.generic import GenericRelation
from django.contrib.contenttypes.models import ContentType

from utils import log_change, tupletuple_to_dict

from reference_numbers import generate_membership_bill_reference_number
from reference_numbers import generate_checknumber, add_checknumber

class BillingEmailNotFound(Exception): pass
class MembershipOperationError(Exception): pass

MEMBER_TYPES = (('P', _('Person')),
                ('S', _('Supporting')),
                ('O', _('Organization')),
                ('H', _('Honorary')))
MEMBER_TYPES_DICT = tupletuple_to_dict(MEMBER_TYPES)

MEMBER_STATUS = (('N', _('New')),
                 ('P', _('Pre-approved')),
                 ('A', _('Approved')),
                 ('D', _('Deleted')))
MEMBER_STATUS_DICT = tupletuple_to_dict(MEMBER_STATUS)


def logging_log_change(sender, instance, created, **kwargs):
    operation = "created" if created else "modified"
    logger.info('%s %s: %s' % (sender.__name__, operation, repr(instance)))

def _get_logs(self):
    '''Gets the log entries related to this object.
    Getter to be used as property instead of GenericRelation'''
    my_class = self.__class__
    ct = ContentType.objects.get_for_model(my_class)
    object_logs = ct.logentry_set.filter(object_id=self.id)
    return object_logs

class Contact(models.Model):
    logs = property(_get_logs)

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

    def delete_if_no_references(self, user):
        person = Q(person=self)
        org = Q(organization=self)
        billing = Q(billing_contact=self)
        tech = Q(tech_contact=self)
        refs = Membership.objects.filter(person | org | billing | tech)
        if refs.count() == 0:
            logger.info("Deleting contact %s: no more references (by %s)" % (
                str(self), str(user)))
            self.logs.delete()
            self.delete()

    def __unicode__(self):
        if self.organization_name:
            return self.organization_name
        else:
            return u'%s %s' % (self.last_name, self.first_name)


class Membership(models.Model):
    class Meta:
        permissions = (
            ("read_members", "Can read member details"),
            ("manage_members", "Can change details, pre-/approve"),
            ("delete_members", "Can delete members"),
        )

    logs = property(_get_logs)

    type = models.CharField(max_length=1, choices=MEMBER_TYPES, verbose_name=_('Membership type'))
    status = models.CharField(max_length=1, choices=MEMBER_STATUS, default='N', verbose_name=_('Membership status'))
    created = models.DateTimeField(auto_now_add=True, verbose_name=_('Membership created'))
    approved = models.DateTimeField(blank=True, null=True, verbose_name=_('Membership approved'))
    last_changed = models.DateTimeField(auto_now=True, verbose_name=_('Membership changed'))
    public_memberlist = models.BooleanField(_('Show in the memberlist'))

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
        if self.type not in MEMBER_TYPES_DICT.keys():
            raise Exception("Illegal member type '%s'" % self.type)
        if self.status not in MEMBER_STATUS_DICT.keys():
            raise Exception("Illegal member status '%s'" % self.status)
        if self.status != 'D':
            if self.type == 'O' and self.person:
                raise Exception("Organization may not have a person contact.")
            if self.type != 'O' and self.organization:
                raise Exception("Non-organization may not have an organization contact.")

            if self.person and self.organization:
                raise Exception("Person-contact and organization-contact are mutually exclusive.")
            if not self.person and not self.organization:
                raise Exception("Either Person-contact or organization-contact must be defined.")
        else:
            if self.person or self.organization or self.billing_contact or self.tech_contact:
                raise Exception("A membership may not have any contacts if it is deleted.")
        super(Membership, self).save(*args, **kwargs)

    def preapprove(self, user):
        if self.status != 'N':
            raise MembershipOperationError("A membership from other state than new can't be preapproved.")
        if user == None:
            msg = "Membership.preapprove() needs user object as a parameter"
            logger.critical("%s" % traceback.format_exc())
            logger.critical(msg)
            raise MembershipOperationError(msg)
        self.status = 'P'
        self.save()
        log_change(self, user, change_message="Preapproved")

    def approve(self, user):
        if self.status != 'P':
            raise MembershipOperationError("A membership from other state than preapproved can't be approved.")
        if user == None:
            msg = "Membership.approve() needs user object as a parameter"
            logger.critical("%s" % traceback.format_exc())
            logger.critical(msg)
            raise MembershipOperationError(msg)
        self.status = 'A'
        self.approved = datetime.now()
        self.save()
        log_change(self, user, change_message="Approved")

    def delete_membership(self, user):
        if self.status == 'D':
            raise MembershipOperationError("A deleted membership can't be deleted.")
        self.status = 'D'
        contacts = [self.person, self.billing_contact, self.tech_contact,
            self.organization]
        self.person = None
        self.billing_contact = None
        self.tech_contact = None
        self.organization = None
        self.save()
        for contact in contacts:
            if contact != None:
                contact.delete_if_no_references(user)
        for alias in self.alias_set.all():
            alias.expire()
        log_change(self, user, change_message="Deleted")

    def valid_aliases(self):
        '''Builds a queryset of all valid aliases'''
        no_expire = Q(expiration_date=None)
        not_expired = Q(expiration_date__lt=datetime.now())
        return Alias.objects.filter(no_expire | not_expired).filter(owner=self)

    def __repr__(self):
        return "<Membership(%s): %s (%i)>" % (self.type, str(self), self.id)

    def __str__(self):
        return unicode(self).encode('ASCII', 'backslashreplace')
    def __unicode__(self):
        if self.organization:
            return self.organization.__unicode__()
        else:
            if self.person:
                return self.person.__unicode__()
            else:
                return "#%d" % self.id


class Alias(models.Model):
    owner = models.ForeignKey('Membership', verbose_name=_('Alias owner'))
    name = models.CharField(max_length=128, unique=True, verbose_name=_('Alias name'))
    account = models.BooleanField(default=False, verbose_name=_('Is UNIX account'))
    created = models.DateTimeField(auto_now_add=True, verbose_name=_('Created'))
    comment = models.CharField(max_length=128, blank=True, verbose_name=_('Comment'))
    expiration_date = models.DateTimeField(blank=True, null=True, verbose_name=_('Alias expiration date'))
    logs = property(_get_logs)

    def expire(self, time=None):
        if time == None:
            time = datetime.now()
        self.expiration_date = time
        self.save()

    @classmethod
    def email_forwards(cls, membership=None, first_name=None, last_name=None,
                       given_names=None):
        "Returns a list of available email forward permutations."
        if membership:
            first_name = membership.person.first_name.lower()
            last_name = membership.person.last_name.lower()
            given_names = membership.person.given_names.lower()
        else:
            first_name = first_name.lower()
            last_name = last_name.lower()
            given_names = given_names.lower()

        permutations = []

        permutations.append(first_name + "." + last_name)
        permutations.append(last_name + "." + first_name)

        non_first_names = []
        initials = []
        for n in given_names.split(" "):
            if n != first_name:
                non_first_names.append(n)
                initials.append(n)

        all_initials_name = []
        for i in initials:
            permutations.append(first_name + "." + i + "." + last_name)
            permutations.append(i + "." + first_name + "." + last_name)
            all_initials_name.append(i)

        all_initials_name.append(last_name)
        permutations.append(".".join(all_initials_name))

        return [perm for perm in permutations
                if cls.objects.filter(name__iexact=perm).count() == 0]

    def __unicode__(self):
        return self.name


class Fee(models.Model):
    type = models.CharField(max_length=1, choices=MEMBER_TYPES, verbose_name=_('Fee type'))
    start = models.DateTimeField(_('Valid from date'))
    sum = models.DecimalField(_('Sum'), max_digits=6, decimal_places=2)

    def __unicode__(self):
        return "Fee for %s, %s euros, %s--" % (self.get_type_display(), str(self.sum), str(self.start))

class BillingCycle(models.Model):
    class Meta:
        permissions = (
            ("read_bills", "Can read billing details"),
            ("manage_bills", "Can manage billing"),
        )

    membership = models.ForeignKey('Membership', verbose_name=_('Membership'))
    start =  models.DateTimeField(default=datetime.now(), verbose_name=_('Start'))
    end =  models.DateTimeField(verbose_name=_('End'))
    sum = models.DecimalField(_('Sum'), max_digits=6, decimal_places=2) # This limits sum to 9999,99
    is_paid = models.BooleanField(default=False, verbose_name=_('Is paid'))
    reference_number = models.CharField(max_length=64, verbose_name=_('Reference number')) # NOT an integer since it can begin with 0 XXX: format
    logs = property(_get_logs)

    def last_bill(self):
        try:
            return self.bill_set.latest("due_date")
        except ObjectDoesNotExist:
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
        return str(self.start.date()) + "--" + str(self.end.date())

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
    logs = property(_get_logs)

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
            'membership_type' : MEMBER_TYPES_DICT[membership.type],
            'membership_type_raw' : membership.type,
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
            'today': datetime.now(),
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
            logger.info('A bill sent as email to %s: %s' % (membership.email,
                repr(Bill)))
        else:
            logger.info('Bill not sent: membership fee zero for %s: %s' % (
                membership.email, repr(Bill)))
        self.billingcycle.bill_sent = True
        self.billingcycle.save()


class Payment(models.Model):
    class Meta:
        permissions = (
            ("can_import", "Can import payment data"),
        )

    """
    Payment object for billing
    """
    # While Payment refers to BillingCycle, the architecture scales to support
    # recording payments that are not related to any billingcycle for future
    # extension
    billingcycle = models.ForeignKey('BillingCycle', verbose_name=_('Cycle'), null=True)
    ignore = models.BooleanField(default=False, verbose_name=_('Ignored payment'))

    reference_number = models.CharField(max_length=64, verbose_name=_('Reference number'), blank=True)
    message = models.CharField(max_length=256, verbose_name=_('Message'), blank=True)
    transaction_id = models.CharField(max_length=30, verbose_name=_('Transaction id'), unique=True)
    payment_day = models.DateTimeField(verbose_name=_('Payment day'))
    amount = models.DecimalField(max_digits=9, decimal_places=2, verbose_name=_('Amount')) # This limits sum to 9999999.99
    type = models.CharField(max_length=64, verbose_name=_('Type'))
    payer_name = models.CharField(max_length=64, verbose_name=_('Payer name'))
    logs = property(_get_logs)

    def __unicode__(self):
        return "%.2f euros (reference '%s')" % (self.amount, self.reference_number)

models.signals.post_save.connect(logging_log_change, sender=Membership)
models.signals.post_save.connect(logging_log_change, sender=Contact)
models.signals.post_save.connect(logging_log_change, sender=Alias)
models.signals.post_save.connect(logging_log_change, sender=BillingCycle)
models.signals.post_save.connect(logging_log_change, sender=Bill)
models.signals.post_save.connect(logging_log_change, sender=Payment)
