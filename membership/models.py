# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from decimal import Decimal
import logging

from membership.billing import pdf
from membership.reference_numbers import barcode_4, group_right,\
    generate_membership_bill_reference_number

logger = logging.getLogger("membership.models")
import traceback

from cStringIO import StringIO

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models import Q, Sum, Count

from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.template.loader import render_to_string
from django.forms import ValidationError

from django.db.models.query import QuerySet

from django.contrib.contenttypes.models import ContentType

from utils import log_change, tupletuple_to_dict

from email_utils import send_as_email, send_preapprove_email, send_duplicate_payment_notice
from email_utils import bill_sender, preapprove_email_sender, duplicate_payment_sender


class BillingEmailNotFound(Exception): pass
class MembershipOperationError(Exception): pass
class PaymentAttachedError(Exception): pass

MEMBER_TYPES = (('P', _('Person')),
                ('S', _('Supporting')),
                ('O', _('Organization')),
                ('H', _('Honorary')))
MEMBER_TYPES_DICT = tupletuple_to_dict(MEMBER_TYPES)

MEMBER_STATUS = (('N', _('New')),
                 ('P', _('Pre-approved')),
                 ('A', _('Approved')),
                 ('S', _('Dissociation requested')),
                 ('I', _('Dissociated')),
                 ('D', _('Deleted')))
MEMBER_STATUS_DICT = tupletuple_to_dict(MEMBER_STATUS)

BILL_TYPES = (
('E', _('Email')),
('P', _('Paper')),
('S', _('SMS'))
)
BILL_TYPES_DICT = tupletuple_to_dict(BILL_TYPES)

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

    def find_memberid(self):
        # Is there better way to find a memberid?
        try:
            return Membership.objects.get(person_id=self.id).id
        except Membership.DoesNotExist:
            pass
        try:
            return Membership.objects.get(organization_id=self.id).id
        except Membership.DoesNotExist:
            pass
        try:
            return Membership.objects.get(billing_contact_id=self.id).id
        except Membership.DoesNotExist:
            pass
        try:
            return Membership.objects.get(tech_contact_id=self.id).id
        except Membership.DoesNotExist:
             return None

    def email_to(self):
        if self.email:
            return '%s <%s>' % (self.name(), self.email)
        return None

    def name(self):
        if self.organization_name:
            return self.organization_name
        else:
            return u'%s %s' % (self.first_name, self.last_name)

    def __unicode__(self):
        if self.organization_name:
            return self.organization_name
        else:
            return u'%s %s' % (self.last_name, self.first_name)


class MembershipManager(models.Manager):
    def sort(self, sortkey):
        qs = MembershipQuerySet(self.model)
        return qs.sort(sortkey)

    def get_query_set(self):
        return MembershipQuerySet(self.model)

class MembershipQuerySet(QuerySet):
    def sort(self, sortkey):
        sortkey = sortkey.strip()
        reverse = False
        if sortkey == "name":
            return self.order_by("person__first_name",
                                 "organization__organization_name")
        elif sortkey == "-name":
            return self.order_by("person__first_name",
                                     "organization__organization_name"
                                     ).reverse()
        elif sortkey == "last_name":
            return self.order_by("person__last_name",
                                 "organization__organization_name")
        elif sortkey == "-last_name":
            return self.order_by("person__last_name",
                                 "organization__organization_name").reverse()
        return self.order_by(sortkey)


class Membership(models.Model):
    class Meta:
        permissions = (
            ("read_members", "Can read member details"),
            ("manage_members", "Can change details, pre-/approve"),
            ("delete_members", "Can delete members"),
            ("dissociate_members", "Can dissociate members"),
            ("request_dissociation_for_member", "Can request dissociation for member"),
        )

    logs = property(_get_logs)

    type = models.CharField(max_length=1, choices=MEMBER_TYPES, verbose_name=_('Membership type'))
    status = models.CharField(max_length=1, choices=MEMBER_STATUS, default='N', verbose_name=_('Membership status'))
    created = models.DateTimeField(auto_now_add=True, verbose_name=_('Membership created'))
    approved = models.DateTimeField(blank=True, null=True, verbose_name=_('Membership approved'))
    last_changed = models.DateTimeField(auto_now=True, verbose_name=_('Membership changed'))
    public_memberlist = models.BooleanField(_('Show in the memberlist'))

    municipality = models.CharField(_('Home municipality'), max_length=128, blank=True)
    nationality = models.CharField(_('Nationality'), max_length=128)
    birth_year = models.IntegerField(_('Year of birth'), null=True, blank=True)
    organization_registration_number = models.CharField(_('Organization registration number'), max_length=15, null=True, blank=True)

    person = models.ForeignKey('Contact', related_name='person_set', verbose_name=_('Person'), blank=True, null=True)
    billing_contact = models.ForeignKey('Contact', related_name='billing_set', verbose_name=_('Billing contact'), blank=True, null=True)
    tech_contact = models.ForeignKey('Contact', related_name='tech_contact_set', verbose_name=_('Technical contact'), blank=True, null=True)
    organization = models.ForeignKey('Contact', related_name='organization_set', verbose_name=_('Organization'), blank=True, null=True)

    extra_info = models.TextField(blank=True, verbose_name=_('Additional information'))

    locked = models.DateTimeField(blank=True, null=True, verbose_name=_('Membership locked'))
    dissociation_requested = models.DateTimeField(blank=True, null=True, verbose_name=_('Dissociation requested'))
    dissociated = models.DateTimeField(blank=True, null=True, verbose_name=_('Member dissociated'))

    objects = MembershipManager()

    def primary_contact(self):
        if self.organization:
            return self.organization
        else:
            return self.person

    def name(self):
        if self.primary_contact():
            return self.primary_contact().name()
        else:
            return unicode(self)

    def email(self):
        return self.primary_contact().email

    def email_to(self):
        return self.primary_contact().email_to()

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
                    return unicode(contact.email_to())
        raise BillingEmailNotFound("Neither billing or administrative contact "+
            "has an email address")

    # https://docs.djangoproject.com/en/dev/ref/models/instances/#django.db.models.Model.clean
    def clean(self):
        if self.type not in MEMBER_TYPES_DICT.keys():
            raise ValidationError("Illegal member type '%s'" % self.type)
        if self.status not in MEMBER_STATUS_DICT.keys():
            raise ValidationError("Illegal member status '%s'" % self.status)
        if self.status != 'D':
            if self.type == 'O' and self.person:
                raise ValidationError("Organization may not have a person contact.")
            if self.type != 'O' and self.organization:
                raise ValidationError("Non-organization may not have an organization contact.")

            if self.person and self.organization:
                raise ValidationError("Person-contact and organization-contact are mutually exclusive.")
            if not self.person and not self.organization:
                raise ValidationError("Either Person-contact or organization-contact must be defined.")
            if not self.municipality:
                raise ValidationError("Municipality can't be null.")
        else:
            if self.person or self.organization or self.billing_contact or self.tech_contact:
                raise ValidationError("A membership may not have any contacts if it is deleted.")

    def save(self, *args, **kwargs):
        try:
            self.full_clean()
        except ValidationError, ve:
            raise ve

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

        ret_items = send_preapprove_email.send_robust(self.__class__, instance=self, user=user)
        for item in ret_items:
            sender, error = item
            if error != None:
                raise error
        logger.info("Membership %s preapproved." % self)

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

    def request_dissociation(self, user):
        if self.status != 'A':
            raise MembershipOperationError("A membership from other state than approved can't be requested for dissociation.")
        if user == None:
            msg = "Membership.request_dissociation() needs user object as a parameter"
            logger.critical("%s" % traceback.format_exc())
            logger.critical(msg)
            raise MembershipOperationError(msg)

        self.status = 'S'
        self.dissociation_requested = datetime.now()
        self.save()
        log_change(self, user, change_message="Dissociation requested")

    def cancel_dissociation_request(self, user):
        if self.status != 'S':
            raise MembershipOperationError("A membership has to be in dissociation requested state for the state to be canceled.")
        if user == None:
            msg = "Membership.cancel_dissociation_request() needs user object as a parameter"
            logger.critical("%s" % traceback.format_exc())
            logger.critical(msg)
            raise MembershipOperationError(msg)

        self.status = 'A'
        self.dissociation_requested = None
        self.save()
        log_change(self, user, change_message="Dissociation request state reverted")

    def dissociate(self, user):
        if self.status not in ('A', 'S'):
            raise MembershipOperationError("A membership from other state than dissociation requested or approved can't be dissociated.")
        if user == None:
            msg = "Membership.dissociate() needs user object as a parameter"
            logger.critical("%s" % traceback.format_exc())
            logger.critical(msg)
            raise MembershipOperationError(msg)

        self.status = 'I'
        self.dissociated = datetime.now()
        self.save()
        log_change(self, user, change_message="Dissociated")

    def delete_membership(self, user):
        if self.status == 'D':
            raise MembershipOperationError("A deleted membership can't be deleted.")
        elif self.status == 'N':
            # must be imported here due to cyclic imports
            from services.models import Service
            logger.info("Deleting services of the membership application %s." % repr(self))
            for service in Service.objects.filter(owner=self):
                service.delete()
            logger.info("Deleting aliases of the membership application %s." % repr(self))
            for alias in self.alias_set.all():
                alias.delete()
        else:
            logger.info("Not deleting services of membership %s." % repr(self))
            logger.info("Expiring aliases of membership %s." % repr(self))
            for alias in self.alias_set.all():
                alias.expire()

        self.status = 'D'
        contacts = [self.person, self.billing_contact, self.tech_contact,
                    self.organization]
        self.person = None
        self.billing_contact = None
        self.tech_contact = None
        self.organization = None
        self.municipality = ''
        self.birth_year = None
        self.organization_registration_number = None
        self.save()
        for contact in contacts:
            if contact != None:
                contact.delete_if_no_references(user)
        log_change(self, user, change_message="Deleted")

    def duplicates(self):
        """
        Finds duplicates of memberships, looks for similar names, emails, phone
        numbers and contact details.  Returns a QuerySet object that doesn't
        include the membership of which duplicates are search for itself.
        """
        qs = Membership.objects

        if self.person and not self.organization:
            name_q = Q(person__first_name__icontains=self.person.first_name.strip(),
                       person__last_name__icontains=self.person.last_name.strip())

            email_q = Q(person__email__contains=self.person.email.strip())
            phone_q = Q(person__phone__icontains=self.person.phone.strip())
            sms_q = Q(person__sms__icontains=self.person.sms.strip())
            # don't match empty sms string
            if self.person.sms.strip():
                contacts_q = email_q | phone_q | sms_q
            else:
                contacts_q = email_q | phone_q

            qs = qs.filter(name_q | contacts_q)
        elif self.organization and not self.person:
            qs = qs.filter(organization__organization_name__icontains=self.organization.organization_name.strip())

        return qs.exclude(id__exact=self.id)

    @classmethod
    def search(cls, query):
        person_contacts = Contact.objects
        org_contacts = Contact.objects

        # Split into words and remove duplicates
        words = set(query.split(" "))

        # Each word narrows the search further
        for word in words:
            # Exact word match when word is "word"
            if word.startswith('"') and word.endswith('"'):
                word = word[1:-1]
                # Search query for people
                f_q = Q(first_name__iexact=word)
                l_q = Q(last_name__iexact=word)
                g_q = Q(given_names__iexact=word)
                person_contacts = person_contacts.filter(f_q | l_q | g_q)

                # Search for organizations
                o_q = Q(organization_name__iexact=word)
                org_contacts = org_contacts.filter(o_q)
            else:
                # Common search parameters
                email_q = Q(email__icontains=word)
                phone_q = Q(phone__icontains=word)
                sms_q = Q(sms__icontains=word)
                common_q = email_q | phone_q | sms_q

                # Search query for people
                f_q = Q(first_name__icontains=word)
                l_q = Q(last_name__icontains=word)
                g_q = Q(given_names__icontains=word)
                person_contacts = person_contacts.filter(f_q | l_q | g_q | common_q)

                # Search for organizations
                o_q = Q(organization_name__icontains=word)
                org_contacts = org_contacts.filter(o_q | common_q)

        # Finally combine matches; all membership for which there are matching
        # contacts or aliases
        person_q = Q(person__in=person_contacts)
        org_q = Q(organization__in=org_contacts)
        alias_q = Q(alias__name__in=words)
        qs = Membership.objects.filter(person_q | org_q | alias_q).distinct()

        qs = qs.order_by("organization__organization_name",
                         "person__last_name",
                         "person__first_name")

        return qs

    @classmethod
    def paper_reminder_sent_unpaid_after(cls, days=14):
        unpaid_filter = Q(billingcycle__is_paid=False)
        type_filter = Q(type='P')
        date_filter = Q(due_date__lt=datetime.now() - timedelta(days=days))
        not_deleted_filter = Q(billingcycle__membership__status__exact='A')
        bill_qs = Bill.objects.filter(unpaid_filter, type_filter, date_filter,
                                      not_deleted_filter)

        membership_ids = set()
        for bill in bill_qs:
            membership_ids.add(bill.billingcycle.membership.id)

        return Membership.objects.filter(id__in=membership_ids)

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

class Fee(models.Model):
    type = models.CharField(max_length=1, choices=MEMBER_TYPES, verbose_name=_('Fee type'))
    start = models.DateTimeField(_('Valid from date'))
    sum = models.DecimalField(_('Sum'), max_digits=6, decimal_places=2)
    vat_percentage = models.IntegerField(_('VAT percentage'))

    def __unicode__(self):
        return "Fee for %s, %s euros, %s%% VAT, %s--" % \
               (self.get_type_display(), str(self.sum), str(self.vat_percentage), str(self.start))


class BillingCycleManager(models.Manager):
    def sort(self, sortkey):
        qs = BillingQuerySet(self.model)
        return qs.sort(sortkey)

    def get_query_set(self):
        return BillingCycleQuerySet(self.model)

class BillingCycleQuerySet(QuerySet):
    def sort(self, sortkey):
        sortkey = sortkey.strip()
        reverse = False
        if sortkey == "name":
            return self.order_by("membership__person__first_name",
                                 "membership__organization__organization_name")
        elif sortkey == "-name":
                return self.order_by("membership__person__first_name",
                        "memership__organization__organization_name").reverse()
        elif sortkey == "last_name":
            return self.order_by("membership__person__last_name",
                                 "membership__organization__organization_name")
        elif sortkey == "-last_name":
            return self.order_by("membership__person__last_name",
                                 "membership__organization__organization_name"
                                 ).reverse()
        elif sortkey == "reminder_count":
            return self.annotate(reminder_sum=Sum('bill__reminder_count')
                                ).order_by('reminder_sum')
        elif sortkey == "-reminder_count":
            return self.annotate(reminder_sum=Sum('bill__reminder_count')
                                ).order_by('reminder_sum').reverse()
        return self.order_by(sortkey)


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

    objects = BillingCycleManager()

    def first_bill_sent_on(self):
        try:
            first_sent_date = self.bill_set.order_by('created')[0].created
            return first_sent_date
        except IndexError:
            # No bills sent yet
            return None

    def last_bill(self):
        try:
            return self.bill_set.latest("due_date")
        except ObjectDoesNotExist:
            return None

    def first_bill(self):
        try:
            return self.bill_set.order_by('due_date')[0]
        except IndexError:
            return None

    def is_first_bill_late(self):
        if self.is_paid:
            return False
        try:
            first_due_date = self.bill_set.order_by('due_date')[0].due_date
        except IndexError:
            # No bills sent yet
            return False
        if datetime.now() > first_due_date:
            return True
        return False

    def is_last_bill_late(self):
        if self.is_paid or self.last_bill() == None:
            return False
        if datetime.now() > self.last_bill().due_date:
            return True
        return False

    def amount_paid(self):
        data = self.payment_set.aggregate(Sum('amount'))['amount__sum']
        if data == None:
            data = Decimal('0')
        return data

    def update_is_paid(self, user=None):
        was_paid = self.is_paid
        total_paid = self.amount_paid()
        if not was_paid and total_paid >= self.sum:
            self.is_paid = True
            self.save()
            logger.info("BillingCycle %s marked as paid, total paid: %.2f." % (
                repr(self), total_paid))
        elif was_paid and total_paid < self.sum:
            self.is_paid = False
            self.save()
            logger.info("BillingCycle %s marked as unpaid, total paid: %.2f." % (
                repr(self), total_paid))

        if user:
            log_change(self, user, change_message="Marked as paid")

    def get_fee(self):
        for_this_type = Q(type=self.membership.type)
        not_before_start = Q(start__lte=self.start)
        fees = Fee.objects.filter(for_this_type, not_before_start)
        valid_fee = fees.latest('start').sum
        return valid_fee

    def get_vat_percentage(self):
        for_this_type = Q(type=self.membership.type)
        not_before_start = Q(start__lte=self.start)
        fees = Fee.objects.filter(for_this_type, not_before_start)
        vat_percentage = fees.latest('start').vat_percentage
        return vat_percentage

    @classmethod
    def get_reminder_billingcycles(cls, memberid=None):
        """
        Get queryset for BillingCycles with missing payments and witch have 2 or more bills already sent.
        :param memberid:
        :return:
        """
        if not settings.ENABLE_REMINDERS:
            return cls.objects.none()

        qs = cls.objects

        # Single membership case
        if memberid:
            logger.info('memberid: %s' % memberid)
            qs = qs.filter(membership__id=memberid)
            qs = qs.exclude(bill__type='P')
            return qs

        # For all memberships in Approved state
        qs = qs.annotate(bills=Count('bill'))
        qs = qs.filter(bills__gt=2,
                       is_paid__exact=False,
                       membership__status='A',
                       membership__id__gt=-1)
        qs = qs.exclude(bill__type='P')
        qs = qs.order_by('start')

        return qs

    @classmethod
    def create_paper_remainder_list(cls, memberid=None):
        """
        Create list of BillingCycles with missing payments and which already don't have paper bill.
        :param memberid: optional member id
        :return: list of billingcycles
        """
        datalist = []
        for cycle in cls.get_reminder_billingcycles(memberid).all():
            # check if paper reminder already sent
            cont = False
            for bill in cycle.bill_set.all():
                if bill.type == 'P':
                    cont=True
                    break
            if cont:
                continue

            datalist.append(cycle)
        return datalist


    def __unicode__(self):
        return str(self.start.date()) + "--" + str(self.end.date())

    def save(self, *args, **kwargs):
        if not self.end:
            self.end = self.start + timedelta(days=365)
            if (self.end.day != self.start.day):
                # Leap day
                self.end += timedelta(days=1)
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
    type = models.CharField(max_length=1, choices=BILL_TYPES, blank=False, null=False, verbose_name=_('Bill type'), default='E')
    logs = property(_get_logs)

    def is_due(self):
        return self.due_date < datetime.now()

    def __unicode__(self):
        return _('Sent on') + ' ' + str(self.created)

    def save(self, *args, **kwargs):
        if not self.due_date:
            self.due_date = datetime.now() + timedelta(days=settings.BILL_DAYS_TO_DUE)
            self.due_date = self.due_date.replace(hour=23, minute=59, second=59)
        super(Bill, self).save(*args, **kwargs)

    def is_reminder(self):
        return self.reminder_count > 0

    # FIXME: different template based on class? should this code be here?
    def render_as_text(self):
        """
        Renders the object as text suitable for sending as e-mail.
        """
        membership = self.billingcycle.membership
        vat = Decimal(self.billingcycle.get_vat_percentage()) / Decimal(100)
        if not self.is_reminder():
            non_vat_amount = (self.billingcycle.sum / (Decimal(1) + vat))
            return render_to_string('membership/bill.txt', {
                'membership_type' : MEMBER_TYPES_DICT[membership.type],
                'membership_type_raw' : membership.type,
                'bill_id': self.id,
                'member_id': membership.id,
                'member_name': membership.name(),
                'billing_contact': membership.billing_contact,
                'billing_name': unicode(membership.get_billing_contact()),
                'street_address': membership.get_billing_contact().street_address,
                'postal_code': membership.get_billing_contact().postal_code,
                'post_office': membership.get_billing_contact().post_office,
                'billing_contact': membership.billing_contact,
                'billingcycle': self.billingcycle,
                'iban_account_number': settings.IBAN_ACCOUNT_NUMBER,
                'bic_code': settings.BIC_CODE,
                'due_date': self.due_date,
                'today': datetime.now(),
                'reference_number': group_right(self.billingcycle.reference_number),
                'sum': self.billingcycle.sum,
                'vat_amount': vat * non_vat_amount,
                'non_vat_amount': non_vat_amount,
                'vat_percentage': self.billingcycle.get_vat_percentage(),
                'barcode': barcode_4(iban = settings.IBAN_ACCOUNT_NUMBER,
                                     refnum = self.billingcycle.reference_number,
                                     duedate = self.due_date,
                                     euros = self.billingcycle.sum)
                })
        else:
            amount_paid = self.billingcycle.amount_paid()
            sum = self.billingcycle.sum - amount_paid
            non_vat_sum = sum / (Decimal(1) + vat)
            return render_to_string('membership/reminder.txt', {
                'membership_type' : MEMBER_TYPES_DICT[membership.type],
                'membership_type_raw' : membership.type,
                'bill_id': self.id,
                'member_id': membership.id,
                'member_name': membership.name(),
                'billing_contact': membership.billing_contact,
                'billing_name': unicode(membership.get_billing_contact()),
                'street_address': membership.get_billing_contact().street_address,
                'postal_code': membership.get_billing_contact().postal_code,
                'post_office': membership.get_billing_contact().post_office,
                'municipality': membership.municipality,
                'billing_email': membership.get_billing_contact().email,
                'email': membership.primary_contact().email,
                'billingcycle': self.billingcycle,
                'iban_account_number': settings.IBAN_ACCOUNT_NUMBER,
                'bic_code': settings.BIC_CODE,
                'today': datetime.now(),
                'latest_recorded_payment': Payment.latest_payment_date(),
                'reference_number': group_right(self.billingcycle.reference_number),
                'original_sum': self.billingcycle.sum,
                'amount_paid': amount_paid,
                'sum': sum,
                'vat_amount': vat * non_vat_sum,
                'non_vat_amount':   non_vat_sum,
                'vat_percentage': self.billingcycle.get_vat_percentage(),
                'barcode': barcode_4(iban = settings.IBAN_ACCOUNT_NUMBER,
                                     refnum = self.billingcycle.reference_number,
                                     duedate = None,
                                     euros = sum)
                })

    # FIXME: Should save sending date
    def send_as_email(self):
        membership = self.billingcycle.membership
        if self.billingcycle.sum > 0:
            ret_items = send_as_email.send_robust(self.__class__, instance=self)
            for item in ret_items:
                sender, error = item
                if error != None:
                    logger.error("%s" % traceback.format_exc())
                    raise error
        else:
            self.billingcycle.is_paid = True
            logger.info('Bill not sent: membership fee zero for %s: %s' % (
                membership.email, repr(Bill)))
        self.billingcycle.save()


    def generate_pdf(self):
        """
        Generate pdf and return pdf content
        """
        buffer = StringIO()
        if self.is_reminder():
            # This is reminder
            p = pdf.PDFReminder(buffer)
        else:
            p = pdf.PDFInvoice(buffer)
        p.addCycle(self.billingcycle)
        p.generate()
        response = buffer.getvalue()
        buffer.close()
        return response

    def bill_subject(self):
        if not self.is_reminder():
            subject = settings.BILL_SUBJECT
        else:
            subject = settings.REMINDER_SUBJECT
        if '%i' in subject:
            subject = subject % self.id
        return subject

    def reference_number(self):
        return self.billingcycle.reference_number

class Payment(models.Model):
    class Meta:
        permissions = (
            ("can_import_payments", "Can import payment data"),
        )

    """
    Payment object for billing
    """
    # While Payment refers to BillingCycle, the architecture scales to support
    # recording payments that are not related to any billingcycle for future
    # extension
    billingcycle = models.ForeignKey('BillingCycle', verbose_name=_('Cycle'), null=True)
    ignore = models.BooleanField(default=False, verbose_name=_('Ignored payment'))
    comment = models.CharField(max_length=64, verbose_name=_('Comment'), null=True)

    reference_number = models.CharField(max_length=64, verbose_name=_('Reference number'), blank=True)
    message = models.CharField(max_length=256, verbose_name=_('Message'), blank=True)
    transaction_id = models.CharField(max_length=30, verbose_name=_('Transaction id'), unique=True)
    payment_day = models.DateTimeField(verbose_name=_('Payment day'))
    amount = models.DecimalField(max_digits=9, decimal_places=2, verbose_name=_('Amount')) # This limits sum to 9999999.99
    type = models.CharField(max_length=64, verbose_name=_('Type'))
    payer_name = models.CharField(max_length=64, verbose_name=_('Payer name'))
    duplicate = models.BooleanField(verbose_name=_('Duplicate payment'), blank=False, null=False, default=False)
    logs = property(_get_logs)

    def __unicode__(self):
        return "%.2f euros (reference '%s', date '%s')" % (self.amount, self.reference_number, self.payment_day)

    def attach_to_cycle(self, cycle, user=None):
        if self.billingcycle:
            raise PaymentAttachedError("Payment %s already attached to BillingCycle %s." % (repr(self), repr(cycle)))

        self.billingcycle = cycle
        self.ignore = False
        self.save()
        logger.info("Payment %s attached to member %s cycle %s." % (repr(self),
            cycle.membership.id, repr(cycle)))
        if user:
            log_change(self, user, change_message="Attached to billing cycle")
        cycle.update_is_paid(user=user)

    def detach_from_cycle(self, user=None):
        if not self.billingcycle:
            return
        cycle = self.billingcycle
        logger.info("Payment %s detached from cycle %s." % (repr(self),
            repr(cycle)))
        self.billingcycle = None
        self.save()
        if user:
            log_change(self, user, change_message="Detached from billing cycle")
        cycle.update_is_paid()


    def send_duplicate_payment_notice(self, user, **kwargs):
        if not user:
            raise Exception('send_duplicate_payment_notice user objects as parameter')
        billingcycle = BillingCycle.objects.get(reference_number=self.reference_number)
        if billingcycle.sum > 0:
            ret_items = send_duplicate_payment_notice.send_robust(self.__class__, instance=self, user=user, billingcycle=billingcycle)
            for item in ret_items:
                sender, error = item
                if error != None:
                    logger.error("%s" % traceback.format_exc())
                    raise error
            log_change(self, user, change_message="Duplicate payment notice sent")

    @classmethod
    def latest_payment_date(cls):
        try:
            return Payment.objects.latest("payment_day").payment_day
        except Payment.DoesNotExist:
            return None

class ApplicationPoll(models.Model):
    """
    Store statistics taken from membership application "where did you
    hear about us" poll.
    """

    membership = models.ForeignKey('Membership', verbose_name=_('Membership'))
    date = models.DateTimeField(auto_now=True, verbose_name=_('Timestamp'))
    answer = models.CharField(max_length=512,verbose_name=_('Service specific data'),
                                  blank=False, null=False)

models.signals.post_save.connect(logging_log_change, sender=Membership)
models.signals.post_save.connect(logging_log_change, sender=Contact)
models.signals.post_save.connect(logging_log_change, sender=BillingCycle)
models.signals.post_save.connect(logging_log_change, sender=Bill)
models.signals.post_save.connect(logging_log_change, sender=Fee)
models.signals.post_save.connect(logging_log_change, sender=Payment)

# These are registered here due to import madness and general clarity
send_as_email.connect(bill_sender, sender=Bill, dispatch_uid="email_bill")
send_preapprove_email.connect(preapprove_email_sender, sender=Membership,
                              dispatch_uid="preapprove_email")
send_duplicate_payment_notice.connect(duplicate_payment_sender, sender=Payment,
                              dispatch_uid="duplicate_payment_notice")
