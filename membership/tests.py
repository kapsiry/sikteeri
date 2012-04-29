# -*- coding: utf-8 -*-
from __future__ import with_statement

import os
import tempfile
import logging
logger = logging.getLogger("tests")

from decimal import Decimal
from datetime import datetime, timedelta
from random import randint
import json

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase
from django.conf import settings
from django.forms import ValidationError
from django.http import HttpResponse, HttpRequest

from models import *
from utils import *
from forms import *
from test_utils import *
from decorators import trusted_host_required
from sikteeri.iptools import IpRangeList
from services.models import *

from reference_numbers import generate_membership_bill_reference_number
from reference_numbers import generate_checknumber, add_checknumber, check_checknumber, group_right
from reference_numbers import barcode_4, canonize_iban, canonize_refnum, canonize_sum, canonize_duedate
from reference_numbers import ReferenceNumberException
from reference_numbers import ReferenceNumberFormatException
from reference_numbers import IBANFormatException, InvalidAmountException
from reference_numbers import DueDateFormatException

from management.commands.makebills import logger as makebills_logger
from management.commands.makebills import makebills
from management.commands.makebills import create_billingcycle
from management.commands.makebills import send_reminder
from management.commands.makebills import can_send_reminder
from management.commands.makebills import MembershipNotApproved

from management.commands.csvbills import process_csv
from management.commands.csvbills import PaymentFromFutureException

__test__ = {
    "tupletuple_to_dict": tupletuple_to_dict,
}

class ReferenceNumberTest(TestCase):
    def test_1234(self):
        self.failUnlessEqual(generate_checknumber("1234"), 4)
    def test_1234_add(self):
        self.assertEqual(add_checknumber("1234"), "12344")
    def test_666666_add(self):
        self.assertEqual(add_checknumber("666666"), "6666668")

    def test_check_refnum(self):
        self.assertTrue(check_checknumber("6666668"))
        self.assertTrue(check_checknumber("42"))
        self.assertFalse(check_checknumber("43"))
        self.assertTrue(check_checknumber("7758474790647489"))
        self.assertFalse(check_checknumber("7758474790647480"))

    def test_uniqueness_of_reference_numbers(self):
        numbers = set([])
        for i in xrange(1, 100):
            for j in xrange(datetime.now().year, datetime.now().year + 11):
                number = generate_membership_bill_reference_number(i, j)
                self.assertFalse(number in numbers)
                numbers.add(number)

    def test_grouping(self):
        self.assertEqual(group_right('1'), '1')
        self.assertEqual(group_right('12'), '12')
        self.assertEqual(group_right('123'), '123')
        self.assertEqual(group_right('12345'), '12345')
        self.assertEqual(group_right('123456'), '1 23456')
        self.assertEqual(group_right('123456789'), '1234 56789')
        self.assertEqual(group_right('12345 333'), '123 45333')
        self.assertEqual(group_right('1111122222'), '11111 22222')
        self.assertEqual(group_right('1112222233333'), '111 22222 33333')
        self.assertEqual(group_right('15222333', group_size=3), '15 222 333')
        self.assertEqual(group_right(u'äkstestÖ'), u'äks testÖ')

    def test_canonize_iban(self):
        self.assertEqual(canonize_iban('FI79 4405 2020 0360 82'), '7944052020036082')
        self.assertEqual(canonize_iban('FI16 5741 3620 4069 56'), '1657413620406956')
        self.assertEqual(canonize_iban(' 16 5741 3620 4069 56 '), '1657413620406956')
        self.assertEqual(canonize_iban('1657413620406956'),       '1657413620406956')
        self.assertRaises(IBANFormatException, canonize_iban, '31231231657413620406956')
        self.assertRaises(IBANFormatException, canonize_iban, 'SE16 5741 3620 4069 56')
        self.assertRaises(IBANFormatException, canonize_iban, 'foobar?')

    def test_canonize_refnum(self):
        self.assertEqual(canonize_refnum('42'),                   '00000000000000000042')
        self.assertEqual(canonize_refnum('32287 22205 1'),        '00000000032287222051')
        self.assertEqual(canonize_refnum('86851 62596 19897'),    '00000868516259619897')
        self.assertEqual(canonize_refnum('559582243294671'),      '00000559582243294671')
        self.assertEqual(canonize_refnum('69 87567 20834 35364'), '00069875672083435364')
        self.assertEqual(canonize_refnum('7 75847 47906 47489'),  '00007758474790647489')
        self.assertEqual(canonize_refnum('78 77767 96566 28687'), '00078777679656628687')
        self.assertEqual(canonize_refnum('8 68624'),              '00000000000000868624')
        self.assertEqual(canonize_refnum(None),                   '00000000000000000000')
        self.assertRaises(ReferenceNumberException, canonize_refnum, '32287 22205 0')
        self.assertRaises(ReferenceNumberFormatException, canonize_refnum, '000000000078777679656628687')
        self.assertRaises(ReferenceNumberFormatException, canonize_refnum, 'not refnum')

    def test_canonize_sum(self):
        self.assertEquals(canonize_sum(euros=35, cents=00), '00003500')
        self.assertEquals(canonize_sum(euros=35, cents=15), '00003515')
        self.assertEquals(canonize_sum(30), '00003000')
        self.assertEquals(canonize_sum(123456), '12345600')
        self.assertEquals(canonize_sum(1000000),     '00000000')
        self.assertEquals(canonize_sum("35"), '00003500')
        self.assertEquals(canonize_sum("250", "99"), '00025099')
        self.assertEquals(canonize_sum("2.10"), '00000210')
        self.assertEquals(canonize_sum(Decimal("150.99")), '00015099')
        self.assertRaises(InvalidAmountException, canonize_sum, -1)
        self.assertRaises(InvalidAmountException, canonize_sum, 123456, 101)

    def test_canonize_duedate(self):
        self.assertEquals(canonize_duedate(datetime(2011, 03 ,20)), '110320')
        self.assertEquals(canonize_duedate(datetime(2011, 03, 31)), '110331')
        self.assertEquals(canonize_duedate(datetime(2021, 12, 31)), '211231')
        self.assertEquals(canonize_duedate(datetime(2010, 10, 10, 16, 52, 30)), '101010')
        self.assertEquals(canonize_duedate(datetime(2010, 10, 10, 23, 59, 59)), '101010')
        self.assertEquals(canonize_duedate(datetime(2010, 10, 10, 0, 1, 0)),    '101010')
        self.assertEquals(canonize_duedate(None), '000000')
        self.assertRaises(ReferenceNumberException, canonize_duedate, ('HETI'))

    # http://www.fkl.fi/www/page/fk_www_1293
    def test_barcode_4(self):
        code = barcode_4('FI79 4405 2020 0360 82', '86851 62596 19897', datetime(2010,6,12), 4883, 15)
        self.assertEqual(code, '479440520200360820048831500000000868516259619897100612')
        code = barcode_4('5810171000000122', '559582243294671', datetime(2012,1,31), 482, 99)
        self.assertEqual(code, '458101710000001220004829900000000559582243294671120131')
        code = barcode_4('FI0250004640001302', '69 87567 20834 35364', datetime(2011,7,24), 693, 80)
        self.assertEqual(code, '402500046400013020006938000000069875672083435364110724')
        code = barcode_4('FI15 6601 0001 5306 41', '7 75847 47906 47489', datetime(2019,12,19), 7444, 54)
        self.assertEqual(code, '415660100015306410074445400000007758474790647489191219')
        code = barcode_4('FI16 8000 1400 0502 67', '78 77767 96566 28687', None, 935, 85)
        self.assertEqual(code, '416800014000502670009358500000078777679656628687000000')
        code = barcode_4('FI73 3131 3001 0000 58', '8 68624', datetime(2013,8,9), 0)
        self.assertEqual(code, '473313130010000580000000000000000000000000868624130809')

        iban = 'FI16 5741 3620 4069 56'
        refnum = '32287 22205 1'
        euros = 35
        cents = 0
        duedate = datetime(2011, 3, 12)
        code = barcode_4(iban, refnum, duedate, euros, cents)
        self.assertEqual(code, '416574136204069560000350000000000000032287222051110312')
        self.assertEqual(len(code), 54)

def create_dummy_member(status, type='P', mid=None):
    if status not in ['N', 'P', 'A']:
        raise Exception("Unknown membership status")
    if type not in ['P', 'S', 'O', 'H']:
        raise Exception("Unknown membership type")
    i = randint(1, 300)
    fname = random_first_name()
    d = {
        'street_address' : 'Testikatu %d'%i,
        'postal_code' : '%d' % (i+1000),
        'post_office' : 'Paska kaupunni',
        'country' : 'Finland',
        'phone' : "%09d" % (40123000 + i),
        'sms' : "%09d" % (40123000 + i),
        'email' : 'user%d@example.com' % i,
        'homepage' : 'http://www.example.com/%d'%i,
        'first_name' : fname,
        'given_names' : '%s %s' % (fname, "Kapsi"),
        'last_name' : random_last_name(),
    }
    contact = Contact(**d)
    contact.save()
    if type == 'O':
        contact.organization_name = contact.name()
        contact.first_name = u''
        contact.last_name = u''
        contact.save()
        membership = Membership(id=mid, type=type, status=status,
                                organization=contact,
                                nationality='Finnish',
                                municipality='Paska kaupunni',
                                extra_info='Hintsunlaisesti semmoisia tietoja.')
    else:
        membership = Membership(id=mid, type=type, status=status,
                                person=contact,
                                nationality='Finnish',
                                municipality='Paska kaupunni',
                                extra_info='Hintsunlaisesti semmoisia tietoja.')
    logger.info("New application %s from %s:." % (str(contact), '::1'))
    membership.save()
    return membership

class MembershipStatusTest(TestCase):
    def setUp(self):
        self.m = create_dummy_member('N')
    def test_status_validations(self):
        for k, v in MEMBER_STATUS:
            if k == 'D':
                continue # deleted memberships don't have contacts
            self.m.status = k
            self.m.save()
        self.m.status = 'X'
        self.assertRaises(ValidationError, self.m.save)
    def test_deleted_should_have_no_contacts(self):
        self.m.status = 'D'
        self.assertRaises(ValidationError, self.m.save)
        self.m.person = None
        self.m.save()

class MembershipTypeTest(TestCase):
    def setUp(self):
        self.m = create_dummy_member('N')
    def test_person_and_organization_contacts_correctly_set(self):
        self.m.organization = self.m.person
        self.assertRaises(ValidationError, self.m.save)
        self.m.type = 'O'
        self.assertRaises(ValidationError, self.m.save)
        self.m.person = None
        self.m.save()

class MembershipFeeTest(TestCase):
    fixtures = ['test_user.json']

    def setUp(self):
        self.user = User.objects.get(id=1)
        membership_p = create_dummy_member('N')
        membership_o = create_dummy_member('N', type='O')
        membership_o.type='O'
        membership_s = create_dummy_member('N')
        membership_s.type='S'
        membership_h = create_dummy_member('N')
        membership_h.type='H'
        for m in [membership_p, membership_o, membership_s, membership_h]:
            m.save()
            m.preapprove(self.user)
            m.approve(self.user)
        self.membership_p = membership_p
        self.membership_o = membership_o
        self.membership_s = membership_s
        self.membership_h = membership_h

    def test_fees(self):
        "Test setting fees and verify that they are set properly"
        now = datetime.now() - timedelta(seconds=5)
        week_ago = datetime.now() - timedelta(days=7)
        P_FEE=30
        S_FEE=500
        O_FEE=60
        H_FEE=0
        soon = datetime.now() + timedelta(hours=1)
        # Old fees
        Fee.objects.create(type='P', start=week_ago, sum=P_FEE/2)
        Fee.objects.create(type='O', start=week_ago, sum=O_FEE/2)
        Fee.objects.create(type='S', start=week_ago, sum=S_FEE/2)
        Fee.objects.create(type='H', start=week_ago, sum=H_FEE/2)
        # Real fees
        p_fee = Fee.objects.create(type='P', start=now, sum=P_FEE)
        o_fee = Fee.objects.create(type='O', start=now, sum=O_FEE)
        s_fee = Fee.objects.create(type='S', start=now, sum=S_FEE)
        h_fee = Fee.objects.create(type='H', start=now, sum=H_FEE)
        # Future fees that must not interfere
        Fee.objects.create(type='P', start=soon, sum=P_FEE*2)
        Fee.objects.create(type='O', start=soon, sum=O_FEE*2)
        Fee.objects.create(type='S', start=soon, sum=S_FEE*2)
        Fee.objects.create(type='H', start=soon, sum=H_FEE*2)
        makebills()
        c_p = BillingCycle.objects.get(membership__type='P')
        c_o = BillingCycle.objects.get(membership__type='O')
        c_s = BillingCycle.objects.get(membership__type='S')
        c_h = BillingCycle.objects.get(membership__type='H')
        self.assertEqual(c_p.sum, P_FEE)
        self.assertEqual(c_o.sum, O_FEE)
        self.assertEqual(c_s.sum, S_FEE)
        self.assertEqual(c_h.sum, H_FEE)


class BillingTest(TestCase):
    # http://docs.djangoproject.com/en/dev/topics/testing/#fixture-loading
    fixtures = ['membership_fees.json', 'test_user.json']

    # http://docs.djangoproject.com/en/dev/topics/testing/#django.core.mail.django.core.mail.outbox

    def setUp(self):
        self.user = User.objects.get(id=1)
        mail.outbox = []

    def tearDown(self):
        pass

    def test_single_preapproved_no_op(self):
        "makebills: preapproved membership no-op"
        membership = create_dummy_member('N')
        membership.preapprove(self.user)
        mail.outbox = []
        makebills()

        self.assertEqual(len(mail.outbox), 0)
        cycles = membership.billingcycle_set.all()
        self.assertEqual(len(cycles), 0)
        membership.delete()

    def test_membership_no_approved_time(self):
        "makebills: approved_time with no entries"
        membership = create_dummy_member('N')
        membership.status = 'A'
        membership.save()

        handler = MockLoggingHandler()
        makebills_logger.addHandler(handler)
        self.assertRaises(MembershipNotApproved, create_billingcycle, membership)

        criticals = handler.messages["critical"]
        self.assertTrue(len(criticals) > 0)

        logged = False
        for critical in criticals:
            if "is missing the approved timestamp. Cannot send bill" in critical:
                logged = True
                break
        self.assertTrue(logged)
        membership.delete()
        makebills_logger.removeHandler(handler)

    def test_membership_approved_time_multiple_entries(self):
        "makebills: approved_time multiple entries"
        membership = create_dummy_member('N')
        membership.preapprove(self.user)
        membership.approve(self.user)
        log_change(membership, self.user, change_message="Approved")
        approve_entries = membership.logs.filter(change_message="Approved")

        t = membership.approved
        self.assertTrue(t != None)

    def test_no_email_if_membership_fee_zero(self):
        membership = create_dummy_member('N', type='H')
        self.assertEqual(len(mail.outbox), 0)
        membership.preapprove(self.user)
        self.assertEqual(len(mail.outbox), 1)
        mail.outbox = []

        membership.approve(self.user)
        makebills()
        bill = Bill.objects.latest('id')
        self.assertEquals(bill.billingcycle.sum, Decimal('0'))

        from models import logger as models_logger
        models_logger.setLevel(level=logging.INFO)
        handler = MockLoggingHandler()
        models_logger.addHandler(handler)

        bill.send_as_email()
        self.assertTrue(bill.billingcycle.is_paid)
        self.assertEqual(len(mail.outbox), 0)

        models_logger.removeHandler(handler)
        infos = handler.messages["info"]
        properly_logged = False
        for info in infos:
            if "Bill not sent:" in info:
                properly_logged = True
        self.assertTrue(properly_logged)


class SingleMemberBillingTest(TestCase):
    # http://docs.djangoproject.com/en/dev/topics/testing/#fixture-loading
    fixtures = ['membership_fees.json', 'test_user.json']

    # http://docs.djangoproject.com/en/dev/topics/testing/#django.core.mail.django.core.mail.outbox

    def setUp(self):
        settings.BILLING_CC_EMAIL = None
        self.user = User.objects.get(id=1)
        membership = create_dummy_member('N')
        membership.preapprove(self.user)
        membership.approve(self.user)
        self.membership = membership
        mail.outbox = []

    def tearDown(self):
        self.membership.delete()

    def test_sending(self):
        settings.BILLING_CC_EMAIL = None
        makebills()
        self.assertEquals(len(mail.outbox), 1)
        m = mail.outbox[0]
        self.assertEquals(m.to[0], self.membership.billing_email())
        self.assertEquals(m.from_email, settings.BILLING_FROM_EMAIL)

    def test_sending_with_cc(self):
        settings.BILLING_CC_EMAIL = "test@example.com"
        makebills()
        self.assertEquals(len(mail.outbox), 1)
        m = mail.outbox[0]
        self.assertEquals(m.to[0], self.membership.billing_email())
        self.assertEquals(m.from_email, settings.BILLING_FROM_EMAIL)
        self.assertEquals(m.extra_headers['CC'], settings.BILLING_CC_EMAIL)
        self.assertTrue(settings.BILLING_CC_EMAIL in m.bcc)

    def test_expired_cycle(self):
        "makebills: before a cycle expires, a new one is created"
        cycle = create_billingcycle(self.membership)
        cycle.starts = datetime.now() - timedelta(days=365)
        cycle.ends = datetime.now() + timedelta(days=27)
        cycle.save()

        makebills()

        self.assertEquals(len(mail.outbox), 1)
        self.assertFalse(cycle.last_bill().is_reminder())

    def test_no_cycle_created(self):
        "makebills: no cycles after an expired membership, should log a warning"
        m = self.membership
        makebills()

        c = m.billingcycle_set.all()[0]
        c.end = datetime.now() - timedelta(hours=1)
        c.save()

        handler = MockLoggingHandler()
        makebills_logger.addHandler(handler)
        makebills()
        makebills_logger.removeHandler(handler)

        warnings = handler.messages["warning"]
        self.assertTrue(len(warnings) > 0)

        logged = False
        for warning in warnings:
            if "no new billing cycle created for" in warning:
                logged = True
                break

        self.assertTrue(logged)

    def test_approved_cycle_and_bill_creation(self):
        "makebills: cycle and bill creation"
        makebills()

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(len(self.membership.billingcycle_set.all()), 1)

        membership2 = create_dummy_member('N')
        membership2.preapprove(self.user)
        membership2.approve(self.user)
        mail.outbox = []
        makebills()

        self.assertEqual(len(membership2.billingcycle_set.all()), 1)
        self.assertEqual(len(mail.outbox), 1)

        c = membership2.billingcycle_set.all()[0]
        self.assertEqual(c.bill_set.count(), 1)
        self.assertEqual(c.last_bill().reminder_count, 0)

    def test_new_billing_cycle_with_previous_paid(self):
        "makebills: new billing cycle with previous already paid"
        m = self.membership

        makebills()
        self.assertEqual(len(m.billingcycle_set.all()), 1)
        self.assertEqual(len(mail.outbox), 1)

        c = m.billingcycle_set.all()[0]
        c.end = datetime.now() + timedelta(days=5)
        c.save()
        b = c.last_bill()
        b.due_date = datetime.now() + timedelta(days=9)
        b.save()
        b.billingcycle.is_paid = True
        b.billingcycle.save()

        makebills()

        self.assertTrue(len(m.billingcycle_set.all()), 2)
        self.assertEqual(len(mail.outbox), 2)

class SingleMemberBillingModelsTest(TestCase):
    fixtures = ['membership_fees.json', 'test_user.json']

    def setUp(self):
        settings.ENABLE_REMINDERS = True
        settings.BILL_DAYS_TO_DUE = 5
        self.user = User.objects.get(id=1)
        membership = create_dummy_member('N')
        membership.preapprove(self.user)
        membership.approve(self.user)
        self.membership = membership
        makebills()
        self.cycle = BillingCycle.objects.get(membership=self.membership)
        self.bill = self.cycle.bill_set.order_by('due_date')[0]

    def tearDown(self):
        self.bill.delete()
        self.cycle.delete()
        self.membership.delete()

    def test_bill_is_reminder(self):
        "models.bill.is_reminder()"
        reminder_bill = send_reminder(self.membership)
        self.assertTrue(reminder_bill.is_reminder())
        self.assertEqual(reminder_bill.reminder_count, 1)
        self.assertFalse(self.bill.is_reminder())
        self.assertEqual(self.bill.reminder_count, 0)
        reminder_bill.delete()

    def test_billing_cycle_last_bill(self):
        "models.Bill.last_bill()"
        reminder_bill = send_reminder(self.membership)
        last_bill = self.cycle.bill_set.latest("due_date")
        self.assertEquals(last_bill.id, reminder_bill.id)
        self.assertNotEquals(last_bill.id, self.bill.id)
        reminder_bill.delete()

    def test_billing_cycle_is_last_bill_late(self):
        "models.Bill.is_last_bill_late()"
        self.assertFalse(self.cycle.is_last_bill_late())
        self.bill.due_date = datetime.now() - timedelta(days=1)
        self.bill.save()
        self.assertTrue(self.cycle.is_last_bill_late())
        self.bill.billingcycle.is_paid = True
        self.bill.billingcycle.save()
        self.cycle = BillingCycle.objects.get(membership=self.membership)
        self.assertFalse(self.cycle.is_last_bill_late())

    def test_billing_payment_attach(self):
        "models.Payment.attach_to_cycle()"
        self.assertFalse(self.cycle.is_paid)
        p1 = Payment(billingcycle=None, amount=self.cycle.sum/2, payment_day=datetime.now(),
             transaction_id="test_billing_payment_attach_1")
        p1.save()
        p2 = Payment(billingcycle=None, amount=self.cycle.sum/2+1, payment_day=datetime.now(),
             transaction_id="test_billing_payment_attach_2")
        p2.save()
        p1.attach_to_cycle(self.cycle)
        self.assertFalse(self.cycle.is_paid)
        p2.attach_to_cycle(self.cycle)
        self.assertTrue(self.cycle.is_paid)
        self.assertRaises(PaymentAttachedError, p1.attach_to_cycle, self.cycle)
        p2.detach_from_cycle()
        self.assertFalse(self.cycle.is_paid)
        p1.detach_from_cycle()
        p1.detach_from_cycle() # Nop

class CanSendReminderTest(TestCase):
    fixtures = ['membership_fees.json', 'test_user.json']

    def setUp(self):
        self.user = User.objects.get(id=1)
        membership = create_dummy_member('N')
        membership.preapprove(self.user)
        membership.approve(self.user)
        self.membership = membership
        makebills()
        self.cycle = BillingCycle.objects.get(membership=self.membership)
        self.bill = self.cycle.bill_set.order_by('due_date')[0]
        settings.ENABLE_REMINDERS = True

    def test_can_send_reminder(self):
        handler = MockLoggingHandler()
        makebills_logger.addHandler(handler)
        now = datetime.now()
        can_send = can_send_reminder(now, Payment.latest_payment_date())
        self.assertFalse(can_send, "Should fail if no payments exist")
        criticals = len(handler.messages['critical'])
        self.assertEqual(criticals, 1, "One log message")
        makebills_logger.removeHandler(handler)

        handler = MockLoggingHandler()
        makebills_logger.addHandler(handler)
        month_ago = datetime.now() - timedelta(days=30)
        p = Payment(billingcycle=self.cycle, amount=5, payment_day=month_ago,
            transaction_id="test_can_send_reminder_1")
        p.save()
        two_weeks_ago = datetime.now() - timedelta(days=14)
        can_send = can_send_reminder(two_weeks_ago, Payment.latest_payment_date())
        self.assertFalse(can_send, "Should fail if payment is old")
        criticals = len(handler.messages['critical'])
        self.assertEqual(criticals, 0, "No critical log messages, got %d" % criticals)
        makebills_logger.removeHandler(handler)

        p = Payment(billingcycle=self.cycle, amount=5, payment_day=now,
            transaction_id="test_can_send_reminder_2")
        p.save()
        can_send = can_send_reminder(month_ago, Payment.latest_payment_date())
        self.assertTrue(can_send, "Should be true with recent payment")

class CSVNoMembersTest(TestCase):
    fixtures = ['membership_fees.json', 'test_user.json']

    def test_file_reading(self):
        "csvbills: test data should have 3 payments, none of which match"
        with open("../membership/fixtures/csv-test.txt", 'r') as f:
            process_csv(f)

        payment_count = Payment.objects.count()
        error = "There should be 3 non-negative payments in the testdata"
        self.assertEqual(payment_count, 3, error)

        no_cycle_q = Q(billingcycle=None)
        nomatch_payments = Payment.objects.filter(~no_cycle_q).count()
        error = "No payments should match without any members in db"
        self.assertEqual(nomatch_payments, 0, error)

class CSVReadingTest(TestCase):
    fixtures = ['membership_fees.json', 'test_user.json']

    def setUp(self):
        self.user = User.objects.get(id=1)
        membership = create_dummy_member('N', mid=11)
        membership.preapprove(self.user)
        membership.approve(self.user)
        cycle_start = datetime(2010, 6, 6)
        self.cycle = BillingCycle(membership=membership, start=cycle_start)
        self.cycle.save()
        self.bill = Bill(billingcycle=self.cycle)
        self.bill.save()

    def test_import_data(self):
        no_cycle_q = Q(billingcycle=None)

        with open("../membership/fixtures/csv-test.txt", 'r') as f:
            process_csv(f)
        payment_count = Payment.objects.filter(~no_cycle_q).count()
        error = "The payment in the sample file should have matched"
        self.assertEqual(payment_count, 1, error)
        payment = Payment.objects.filter(billingcycle=self.cycle).latest("payment_day")
        cycle = BillingCycle.objects.get(pk=self.cycle.pk)
        self.assertEqual(cycle.reference_number, payment.reference_number)
        self.assertTrue(cycle.is_paid)

    def test_duplicate_payment(self):
        no_cycle_q = Q(billingcycle=None)

        with open("../membership/fixtures/csv-test-duplicate.txt", 'r') as f:
            process_csv(f)
        payment_match_count = Payment.objects.filter(~no_cycle_q).count()
        error = "The payment in the sample file should have matched"
        self.assertEqual(payment_match_count, 1, error)
        self.assertEqual(Payment.objects.count(), 2)
        payment = Payment.objects.filter(billingcycle=self.cycle).latest("payment_day")
        cycle = BillingCycle.objects.get(pk=self.cycle.pk)
        self.assertEqual(cycle.reference_number, payment.reference_number)
        self.assertTrue(cycle.is_paid)

    def test_future_payment(self):
        error = "Should fail on payment in the future"
        with open("../membership/fixtures/csv-future.txt", 'r') as f:
            self.assertRaises(PaymentFromFutureException, process_csv, f)

class LoginRequiredTest(TestCase):
    fixtures = ['membpership_fees.json', 'test_user.json']

    def setUp(self):
        self.urls = ['/membership/memberships/new/',
                     '/membership/memberships/preapproved/',
                     '/membership/memberships/preapproved-plain/',
                     '/membership/memberships/approved/',
                     '/membership/memberships/approved-emails/',
                     '/membership/memberships/deleted/',
                     '/membership/memberships/convert_to_an_organization/1/'
                     '/membership/memberships/',
                     '/membership/bills/unpaid/',
                     '/membership/bills/',
                     '/membership/payments/unknown/',
                     '/membership/payments/ignored/',
                     '/membership/payments/',
                     '/membership/testemail/',
                     ]

    def test_views_with_login(self):
        "Request a page that is protected with @login_required"

        # Get the page without logging in. Should result in 302.
        for url in self.urls:
            response = self.client.get(url)
            self.assertRedirects(response, '/login/?next=%s' % url)

        login = self.client.login(username='admin', password='dhtn')
        self.failUnless(login, 'Could not log in')

        # Request a page that requires a login
        for url in self.urls:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['user'].username, 'admin')

class TrustedHostTest(TestCase):
    def setUp(self):
        self.urls = ['/membership/admtool/1',
                     '/membership/admtool/lookup/alias/test',
                     '/membership/metrics/',
                     '/membership/public_memberlist/',
                     '/membership/unpaid_members/',
                     ]
        self.oldhosts = settings.TRUSTED_HOSTS

    def tearDown(self):
        settings.TRUSTED_HOSTS = self.oldhosts

    def test_views_with_ipaddr(self):
        "Request a page that is protected with @login_required"

        # Get the page with an untrusted address 403.
        settings.TRUSTED_HOSTS = ['13.13.13.13']
        for url in self.urls:
            response = self.client.get(url)
            self.assertEquals(response.status_code, 403)

        settings.TRUSTED_HOSTS = ['127.0.0.1']
        # Request a page that requires a trusted client address
        for url in self.urls:
            response = self.client.get(url)
            # Code should be 404 or 200
            if response.status_code == 404:
                continue
            self.assertEqual(response.status_code, 200)

class MemberApplicationTest(TestCase):
    fixtures = ['membership_fees.json', 'test_user.json']

    def setUp(self):
        self.user = User.objects.get(id=1)
        self.post_data = {
            "first_name": u"Yrjö",
            "given_names": u"Yrjö Kapsi",
            "last_name": u"Äikäs",
            "street_address": "Vasagatan 9",
            "postal_code": "90230",
            "post_office": "VAASA",
            "phone": "0123123123",
            "sms": "0123123123",
            "email": "veijo.invalid@valpas.kapsi.fi",
            "homepage": "",
            "nationality": "Suomi",
            "country": "Suomi",
            "municipality": "Vaasa",
            "extra_info": u"Mää oon testikäyttäjä.",
            "unix_login": "luser",
            "email_forward": "y.aikas",
            "mysql_database": "yes",
            "postgresql_database": "yes",
            "login_vhost": "yes",
        }

    def test_do_application(self):
        response = self.client.post('/membership/application/person/', self.post_data)
        self.assertRedirects(response, '/membership/application/person/success/')
        new = Membership.objects.latest("id")
        self.assertEquals(new.person.first_name, u"Yrjö")


    def test_redundant_email_alias(self):
        self.post_data['unix_login'] = 'fname.lname'
        self.post_data['email_forward'] = 'fname.lname'
        response = self.client.post('/membership/application/person/', self.post_data)
        self.assertRedirects(response, '/membership/application/person/success/')
        new = Membership.objects.latest("id")
        self.assertEquals(new.person.first_name, u"Yrjö")

    def test_clean_ajax_output(self):
        post_data = self.post_data.copy()
        post_data['first_name'] = u'<b>Yrjö</b>'
        post_data['extra_info'] = '<iframe src="http://www.kapsi.fi" width=200 height=100></iframe>'
        response = self.client.post('/membership/application/person/', post_data)
        self.assertRedirects(response, '/membership/application/person/success/')
        new = Membership.objects.latest("id")
        self.assertEquals(new.person.first_name, u"<b>Yrjö</b>")

        login = self.client.login(username='admin', password='dhtn')
        self.failUnless(login, 'Could not log in')
        json_response = self.client.post('/membership/application/handle_json/',
                                         json.dumps({"requestType": "MEMBERSHIP_DETAIL", "payload": new.id}),
                                         content_type="application/json")
        self.assertEqual(json_response.status_code, 200)
        json_dict = json.loads(json_response.content)
        self.assertEqual(json_dict['contacts']['person']['first_name'],
                         u'&lt;b&gt;Yrjö&lt;/b&gt;')
        self.assertEqual(json_dict['extra_info'],
                         '&lt;iframe src=&quot;http://www.kapsi.fi&quot; width=200 height=100&gt;&lt;/iframe&gt;')


    def _validate_alias(self, alias):
        json_response = self.client.post('/membership/application/handle_json/',
            json.dumps({"requestType": "VALIDATE_ALIAS", "payload": alias}),
                       content_type="application/json")
        self.assertEqual(json_response.status_code, 200)
        json_dict = json.loads(json_response.content)
        return json_dict

    def test_validate_alias_ajax(self):
        alias = Alias(name='validalias', owner_id=1)
        alias.save()
        result = self._validate_alias('usernotfound')
        self.assertEqual(result['exists'], False)
        self.assertEqual(result['valid'], True)
        result = self._validate_alias('user-')
        self.assertEqual(result['exists'], False)
        self.assertEqual(result['valid'], False)
        result = self._validate_alias('validalias')
        self.assertEqual(result['exists'], True)
        self.assertEqual(result['valid'], True)
        alias.delete()

class PhoneNumberFieldTest(TestCase):
    def setUp(self):
        self.field = PhoneNumberField()

    def test_too_short(self):
        self.assertRaises(ValidationError, self.field.clean, "012")

    def test_too_long(self):
        self.assertRaises(ValidationError, self.field.clean, "012345678901234567890")

    def test_begins_with_bad_char(self):
        self.assertRaises(ValidationError, self.field.clean, "12345")

    def test_number(self):
        self.assertEquals(u"0123456", self.field.clean(u"0123456"))

    def test_parens(self):
        self.assertEquals(u"0400123123", self.field.clean(u"(0400) 123123"))

    def test_dash_delimiter(self):
        self.assertEquals(u"0400123123", self.field.clean(u"0400-123123"))

    def test_space_delimiter(self):
        self.assertEquals(u"0400123123", self.field.clean(u"0400 123123"))

    def test_strippable_spaces(self):
        self.assertEquals(u"0400123123", self.field.clean(u" 0400 123123  "))

    def test_begins_with_plus(self):
        self.assertEquals(u"+358401231111", self.field.clean(u"+358 40 123 1111"))

    def test_dash_delimiter_begins_with_plus(self):
        self.assertEquals(u"+358400123123", self.field.clean(u"+358-400-123123 "))

class LoginFieldTest(TestCase):
    def setUp(self):
        self.field = LoginField()

    def test_valid(self):
        self.assertEquals(u"testuser", self.field.clean(u"testuser"))
        self.assertEquals(u"testuser2", self.field.clean(u"testuser2"))
        self.assertEquals(u"a1b2c4", self.field.clean(u"a1b2c4"))
        self.assertEquals(u"user.name", self.field.clean(u"user.name"))
        self.assertEquals(u"user-name", self.field.clean(u"user-name"))
    def test_uppercase(self):
        self.assertEquals(u"testuser", self.field.clean(u"TestUser"))

    def test_too_short(self):
        self.assertRaises(ValidationError, self.field.clean, "a")

    def test_too_long(self):
        self.assertRaises(ValidationError, self.field.clean, "abcdabcdabcdabbafoobar")

    def test_begins_with_bad_char(self):
        self.assertRaises(ValidationError, self.field.clean, "_foo")
        self.assertRaises(ValidationError, self.field.clean, " foo")

    def test_ends_with_bad_char(self):
        self.assertRaises(ValidationError, self.field.clean, "user!")
        self.assertRaises(ValidationError, self.field.clean, "user-")
        self.assertRaises(ValidationError, self.field.clean, "user.")
        self.assertRaises(ValidationError, self.field.clean, "user_")

    def test_number(self):
        self.assertRaises(ValidationError, self.field.clean, "1234")
        self.assertRaises(ValidationError, self.field.clean, "1foobar")

    def test_parens(self):
        self.assertRaises(ValidationError, self.field.clean, "abcd(foo)")

    def test_space(self):
        self.assertRaises(ValidationError, self.field.clean, "test user")


class MemberListTest(TestCase):
    fixtures = ['membership_fees.json', 'test_user.json']
    def setUp(self):
        self.user = User.objects.get(id=1)
        self.m1 = create_dummy_member('N')
        self.m1.preapprove(self.user)
        self.m1.approve(self.user)
        self.m2 = create_dummy_member('N')
        self.m2.preapprove(self.user)
        self.m3 = create_dummy_member('N')

    def tearDown(self):
        pass

    def test_renders_member_id(self):
        login = self.client.login(username='admin', password='dhtn')
        self.failUnless(login, 'Could not log in')

        response = self.client.get('/membership/memberships/approved/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('<span class="member_id">#%i</span>' % self.m1.id in response.content)

        response = self.client.get('/membership/memberships/preapproved/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('<span class="member_id">#%i</span>' % self.m2.id in response.content)

        response = self.client.get('/membership/memberships/new/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('<li class="list_item preapprovable" id="%i">' % self.m3.id in response.content)

class MemberDeletionTest(TestCase):
    fixtures = ['membership_fees.json', 'test_user.json']
    def setUp(self):
        self.user = User.objects.get(id=1)

    def test_application_deletion(self):
        m = create_dummy_member('N')
        a = Alias(owner=m, name=Alias.email_forwards(m)[0])
        a.save()
        self.assertEquals(Alias.objects.all().count(), 1)

        s = Service(servicetype=ServiceType.objects.get(servicetype='Email alias'),
                    alias=a, owner=m, data=a.name)
        s.save()
        self.assertEquals(Service.objects.all().count(), 1)

        m.delete_membership(self.user)
        self.assertEquals(Service.objects.all().count(), 0)
        self.assertEquals(Alias.objects.all().count(), 0)

    def test_preapproved_deletion(self):
        m = create_dummy_member('N')
        a = Alias(owner=m, name=Alias.email_forwards(m)[0])
        a.save()
        s = Service(servicetype=ServiceType.objects.get(servicetype='Email alias'),
                    alias=a, owner=m, data=a.name)
        s.save()
        self.assertEquals(Service.objects.all().count(), 1)
        self.assertEquals(Alias.objects.all().count(), 1)
        m.preapprove(self.user)

        m.delete_membership(self.user)
        self.assertEquals(Service.objects.all().count(), 1)
        self.assertEquals(Alias.objects.all().count(), 1)
        self.assertFalse(Alias.objects.all()[0].is_valid())


class MetricsInterfaceTest(TestCase):
    def setUp(self):
        self.orig_trusted = settings.TRUSTED_HOSTS
        settings.TRUSTED_HOSTS = ['127.0.0.1']

    def tearDown(self):
        settings.TRUSTED_HOSTS = self.orig_trusted

    def test_membership_statuses(self):
        response = self.client.get('/membership/metrics/')
        self.assertEqual(response.status_code, 200)
        d = json.loads(response.content)
        self.assertTrue(d.has_key(u'memberships'))
        for key in [u'new', u'preapproved', u'approved', u'deleted']:
            self.assertTrue(d[u'memberships'].has_key(key))
        self.assertTrue(d.has_key(u'bills'))
        for key in [u'unpaid_count', u'unpaid_sum']:
            self.assertTrue(d[u'bills'].has_key(key))

class IpRangeListTest(TestCase):
    def test_rangelist(self):
        list1 = IpRangeList('127.0.0.1', '10.0.0.0/8', '127.0.0.2')
        self.assertTrue('127.0.0.1' in list1)
        self.assertTrue('10.0.0.0' in list1)
        self.assertTrue('10.0.0.1' in list1)
        self.assertTrue('10.1.232.255' in list1)
        self.assertFalse('11.0.0.0' in list1)
        self.assertTrue('127.0.0.2' in list1)
        self.assertFalse('127.0.0.3' in list1)
        iplist = ['127.0.0.1', '1.2.3.4']
        self.assertFalse('11.0.0.0' in IpRangeList(*iplist))
        self.assertTrue('1.2.3.4' in IpRangeList(*iplist))
        self.assertFalse('127.0.0.1' in IpRangeList())

@trusted_host_required
def dummyView(request, *args, **kwargs):
    return HttpResponse('OK', mimetype='text/plain')

class DecoratorTest(TestCase):
    def setUp(self):
        settings.TRUSTED_HOSTS = ['127.0.0.1', '10.0.0.0/8']

    def test_require_host(self):
        request = HttpRequest()
        request.META['REMOTE_ADDR'] = '127.0.0.1'
        response1 = dummyView(request)
        self.assertEqual(response1.status_code, 200)

        request.META['REMOTE_ADDR'] = '99.99.99.99'
        response2 = dummyView(request)
        self.assertEqual(response2.status_code, 403)


class DuplicateMembershipDetectionTest(TestCase):
    def test_has_duplicate_membership(self):
        m1 = create_dummy_member('N')
        m1.save()

        m2 = create_dummy_member('N')
        m2.save()
        m2.person.first_name = m1.person.first_name
        m2.person.last_name = m1.person.last_name
        m2.person.save()

        self.assertEquals(len(m1.duplicates()), 1)
        self.assertEquals(m1.duplicates()[0].id, m2.id)
        self.assertEquals(len(m2.duplicates()), 1)
        self.assertEquals(m2.duplicates()[0].id, m1.id)

    def test_same_last_name(self):
        m1 = create_dummy_member('N')
        m1.save()

        m2 = create_dummy_member('N')
        m2.save()
        m2.person.last_name = m1.person.last_name
        m2.person.save()

        self.assertEquals(len(m1.duplicates()), 0)

    def test_has_duplicate_organization(self):
        m1 = create_dummy_member('N', type='O')
        m1.save()

        m2 = create_dummy_member('N', type='O')
        m2.save()
        m2.organization.organization_name = m1.organization.organization_name
        m2.organization.save()

        self.assertEquals(len(m1.duplicates()), 1)
        self.assertEquals(m1.duplicates()[0].id, m2.id)
        self.assertEquals(len(m2.duplicates()), 1)
        self.assertEquals(m2.duplicates()[0].id, m1.id)

    def test_duplicate_phone(self):
        m1 = create_dummy_member('N')
        m1.save()

        m2 = create_dummy_member('N')
        m2.save()
        m2.person.phone = m1.person.phone
        m2.person.save()

        self.assertEquals(len(m1.duplicates()), 1)


class MembershipSearchTest(TestCase):
    def test_find_by_first_name(self):
        pass

    def test_find_by_last_name(self):
        pass

    def test_find_by_organization_name(self):
        pass

    def test_find_by_alias(self):
        pass
