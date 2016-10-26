# -*- coding: utf-8 -*-
from __future__ import with_statement

import calendar
from datetime import datetime, timedelta
from decimal import Decimal

from StringIO import StringIO

import os
import os.path
import logging
import json

from django.core.mail import EmailMessage
from django.core.management import call_command

logger = logging.getLogger("membership.tests")

from django.contrib.auth.models import User
from django.core import mail
from django.core.exceptions import ValidationError
from django.conf import settings
from django.db.models import Q
from django.test import TestCase
from django.http import HttpResponse, HttpRequest
from django.utils.translation import ugettext_lazy as _

from membership import email_utils
from membership.models import (Bill, BillingCycle, Contact, CancelledBill, Membership,
                               MembershipOperationError, MembershipAlreadyStatus,
                               Fee, Payment, PaymentAttachedError, MEMBER_STATUS)
from membership.models import logger as models_logger
from membership import reference_numbers
from membership.utils import tupletuple_to_dict, log_change
from membership.forms import LoginField, PhoneNumberField, OrganizationRegistrationNumber
from membership.test_utils import create_dummy_member, MockLoggingHandler
from membership.decorators import trusted_host_required
from sikteeri.iptools import IpRangeList
from services.models import Service, ServiceType, Alias
from membership.billing.procountor_csv import create_csv
from membership.reference_numbers import generate_membership_bill_reference_number
from membership.reference_numbers import generate_checknumber, add_checknumber, check_checknumber, group_right
from membership.reference_numbers import barcode_4, canonize_iban, canonize_refnum, canonize_sum, canonize_duedate
from membership.reference_numbers import ReferenceNumberException
from membership.reference_numbers import ReferenceNumberFormatException
from membership.reference_numbers import IBANFormatException, InvalidAmountException
from membership.management.commands.makebills import logger as makebills_logger
from membership.management.commands.makebills import makebills
from membership.management.commands.makebills import create_billingcycle
from membership.management.commands.makebills import send_reminder
from membership.management.commands.makebills import can_send_reminder
from membership.management.commands.makebills import MembershipNotApproved
from membership.management.commands.csvbills import process_op_csv, process_procountor_csv
from membership.management.commands.csvbills import PaymentFromFutureException, RequiredFieldNotFoundException

__test__ = {
    "tupletuple_to_dict": tupletuple_to_dict,
}


def open_test_data(file):
    basedir = os.path.dirname(__file__)
    data_file = os.path.join(basedir, 'test_data', file)
    return open(data_file, 'r')


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
        Fee.objects.create(type='P', start=week_ago, sum=P_FEE/2,
                           vat_percentage=24)
        Fee.objects.create(type='O', start=week_ago, sum=O_FEE/2,
                           vat_percentage=24)
        Fee.objects.create(type='S', start=week_ago, sum=S_FEE/2,
                           vat_percentage=24)
        Fee.objects.create(type='H', start=week_ago, sum=H_FEE/2,
                           vat_percentage=24)
        # Real fees
        p_fee = Fee.objects.create(type='P', start=now, sum=P_FEE,
                                   vat_percentage=24)
        o_fee = Fee.objects.create(type='O', start=now, sum=O_FEE,
                                   vat_percentage=24)
        s_fee = Fee.objects.create(type='S', start=now, sum=S_FEE,
                                   vat_percentage=24)
        h_fee = Fee.objects.create(type='H', start=now, sum=H_FEE,
                                   vat_percentage=24)
        # Future fees that must not interfere
        Fee.objects.create(type='P', start=soon, sum=P_FEE*2,
                           vat_percentage=24)
        Fee.objects.create(type='O', start=soon, sum=O_FEE*2,
                           vat_percentage=24)
        Fee.objects.create(type='S', start=soon, sum=S_FEE*2,
                           vat_percentage=24)
        Fee.objects.create(type='H', start=soon, sum=H_FEE*2,
                           vat_percentage=24)
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

        self.assertIsNotNone(membership.approved)

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
        self.assertEquals(CancelledBill.objects.count(), 0)

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
        self.assertEquals(CancelledBill.objects.count(), 0)

    def test_new_billing_cycle_with_previous_paid(self):
        "makebills: new billing cycle with previous already paid"
        m = self.membership

        makebills()
        self.assertEqual(len(m.billingcycle_set.all()), 1)
        self.assertEqual(len(mail.outbox), 1)

        dt = datetime.now()
        c = m.billingcycle_set.all()[0]
        c.end = datetime(dt.year, dt.month, calendar.monthrange(dt.year, dt.month)[1], 23, 59, 59)
        c.save()
        b = c.last_bill()
        b.due_date = datetime(dt.year, dt.month, 1) + timedelta(days = 7)
        b.save()
        b.billingcycle.is_paid = True
        b.billingcycle.save()

        makebills()

        self.assertEqual(len(m.billingcycle_set.all()), 2)
        self.assertEqual(len(mail.outbox), 2)


class ProcountorExportTest(TestCase):
    # Allowable bookkeeping account ids
    BOOK_ACCOUNTS = ['9039', '9037', '9038']

    fixtures = ['membership_fees.json', 'test_user.json']

    def setUp(self):
        settings.BILLING_CC_EMAIL = None
        self.user = User.objects.get(id=1)
        membership = create_dummy_member('N')
        membership.preapprove(self.user)
        membership.approve(self.user)
        self.membership = membership
        mail.outbox = []
        makebills()
        self.assertEquals(len(mail.outbox), 1)

    def get_procountor_email(self):
        TARGET_EMAIL = 'test@example.com'
        mail_count = len(mail.outbox)
        call_command('procountor_export', '--email', TARGET_EMAIL,
                     stdout=StringIO())
        self.assertEquals(len(mail.outbox), mail_count + 1)
        self.assertListEqual(mail.outbox[-1].to, [TARGET_EMAIL])
        message = mail.outbox[-1]
        return message

    def get_procountor_console(self):
        mail_count = len(mail.outbox)
        out = StringIO()
        call_command('procountor_export', stdout=out)
        self.assertEquals(len(mail.outbox), mail_count)
        return out.getvalue()

    def test_procountor_export_email_contains_csv_attachment(self):
        message = self.get_procountor_email()
        self.assertIsInstance(message, EmailMessage)
        self.assertTrue('Sikteerin Procountor-vienti' in message.subject)
        self.assertEquals(len(message.attachments), 1)
        attach_name, attach_content, attach_mime = message.attachments[0]
        self.assertTrue(attach_name.endswith(".csv"))
        self.assertEquals(attach_mime, 'text/csv')

    def check_procountor_csv_contains_two_lines_per_bill(self):
        message = self.get_procountor_email()
        __, attach_content, __ = message.attachments[0]
        # For every one non-reminder billing cycle we expect two lines of CSV
        billingcycle_count = BillingCycle.objects.count()
        csv_lines = attach_content.splitlines()
        self.assertEqual(len(csv_lines), billingcycle_count * 2)

    def test_procountor_csv_contains_bill(self):
        self.assertEquals(Bill.objects.count(), 1)
        self.check_procountor_csv_contains_two_lines_per_bill()

    def test_procountor_csv_contains_bill_only_and_not_reminder(self):
        self.assertEquals(Bill.objects.count(), 1)
        self.check_procountor_csv_contains_two_lines_per_bill()
        send_reminder(self.membership)
        self.assertEquals(Bill.objects.count(), 2)
        self.assertEquals(BillingCycle.objects.count(), 1)
        self.check_procountor_csv_contains_two_lines_per_bill()

    def test_procountor_csv_format_email(self):
        message = self.get_procountor_email()
        __, attach_content, __ = message.attachments[0]
        self.check_procountor_csv_format(attach_content)

    def test_procountor_csv_format_console(self):
        csv_data = self.get_procountor_console()
        self.check_procountor_csv_format(csv_data)

    def test_procountor_csv_format_organization_member(self):
        membership = create_dummy_member('N', type='O')
        membership.preapprove(self.user)
        membership.approve(self.user)
        makebills()
        csv_data = self.get_procountor_console()
        self.check_procountor_csv_format(csv_data)

    def test_procountor_csv_format_supporting_member(self):
        membership = create_dummy_member('N', type='S')
        membership.preapprove(self.user)
        membership.approve(self.user)
        makebills()
        csv_data = self.get_procountor_console()
        self.check_procountor_csv_format(csv_data)

    def test_procountor_csv_format_honorary_member(self):
        membership = create_dummy_member('N', type='H')
        membership.preapprove(self.user)
        membership.approve(self.user)
        makebills()
        csv_data = self.get_procountor_console()
        self.check_procountor_csv_format(csv_data)

    def check_procountor_csv_format(self, csv_data):
        bill_amounts = {}
        lineitem_totals = {}
        current_bill_id = None
        for csv_line in csv_data.splitlines():
            columns = csv_line.split(";")
            self.assertEquals(len(columns), 44)
            if columns[1-1] != '':
                # Laskutietue

                # Format validity checks first
                (
                    bill_type,                  # 1     X
                    currency_code,              # 2
                    reference_number,           # 3
                    iban_account,               # 4
                    organization_id,            # 5
                    payment_type,               # 6
                    other_party_name,           # 7     (X)
                    delivery_method,            # 8
                    discount_percentage,        # 9
                    includes_vat_code,          # 10
                    cancel_bill_code,           # 11
                    interest_percentage,        # 12
                    bill_date,                  # 13
                    delivery_date,              # 14
                    due_date,                   # 15
                    other_party_address,        # 16
                    billing_address,            # 17    (X)
                    delivery_address,           # 18
                    bill_notes_public,          # 19
                    bill_notes_private,         # 20
                    email_address,              # 21
                    payment_date,               # 22
                    currency_rate,              # 23
                    bill_amount,                # 24
                    vat_percentage,             # 25
                    billing_channel,            # 26
                    e_bill_id,                  # 27    (X)
                    order_reference,            # 28
                    book_by_rows_code,          # 29
                    deprecated_1,               # 30  DEPRECATED Finvoice address
                    deprecated_2,               # 31  DEPRECATED Finvoice address2
                    customer_id,                # 32
                    automatic_billing_code,     # 33
                    attachment_file_name,       # 34
                    contact_person,             # 35
                    other_party_swift,          # 36    (X)
                    e_bill_operator,            # 37    (X)
                    other_party_ovt,            # 38    (X)
                    billing_id,                 # 39
                    factoring_finance_id,       # 40
                    vat_country_code,           # 41
                    language_code,              # 42
                    cash_discount_days,         # 43
                    cash_discount_percentage,   # 44
                    ) = columns
                # 1
                self.assertTrue(bill_type in ['O', 'M', 'T', 'K', 'N'], "Bill type is required")
                # 2
                if currency_code != '':
                    self.assertEqual(currency_code, 'EUR')
                # 3
                if reference_number != '':
                    self.assertTrue(reference_numbers.check_checknumber(reference_number))
                    self.assertTrue(len(reference_number) <= 20)
                # 4
                if iban_account != '':
                    self.assertEqual(iban_account, settings.IBAN_ACCOUNT_NUMBER)
                # 5
                if organization_id != '':
                    self.assertTrue(len(organization_id) <= 40)
                # 6
                if payment_type != '':
                    self.assertTrue(
                        payment_type in ['tilisiirto', 'suoraveloitus', 'suoramaksu', 'clearing',
                                         'luottokorttiveloitus', 'ulkomaanmaksu'])
                # 7
                self.assertTrue(0 < len(other_party_name) <= 80,
                                "Business partner name non-empty")
                # 8
                if delivery_method != '':
                    self.assertTrue(
                        delivery_method in ['postitus', 'verkossa', 'rahtikuljetus', 'kuriiripalvelu', 'vr cargo',
                                            'linja-auto', 'noudettava']
                    )
                # 9
                if discount_percentage != '':
                    self.assertTrue(0 <= float(discount_percentage) <= 100)
                # 10
                if includes_vat_code != '':
                    self.assertTrue(includes_vat_code in ['t', 'f'])
                # 11
                if cancel_bill_code != '':
                    self.assertTrue(cancel_bill_code in ['t', 'f'])
                # 12
                if interest_percentage != '':
                    self.assertTrue(0 <= float(interest_percentage) <= 100)
                # 13
                if bill_date != '':
                    bill_date = datetime.strptime(bill_date, "%d.%m.%Y")
                # 14
                if delivery_date != '':
                    delivery_date = datetime.strptime(delivery_date, "%d.%m.%Y")
                # 15
                if due_date != '':
                    due_date = datetime.strptime(due_date, "%d.%m.%Y")
                # 16
                if other_party_address != '':
                    self.assertTrue(len(other_party_address) <= 255)
                    _parts = other_party_address.split("\\")
                    if len(_parts) == 5:
                        _tarkenne, _katuosoite, _postinumero, _kaupunki, _maakoodi = _parts
                    elif len(_parts) == 4:
                        _tarkenne = None
                        _katuosoite, _postinumero, _kaupunki, _maakoodi = _parts
                # 17
                if billing_channel == '2' or billing_address != '':
                    self.assertTrue(len(billing_address) <= 255)
                    _parts = billing_address.split("\\")
                    if len(_parts) == 6:
                        _nimi, _tarkenne, _katuosoite, _postinumero, _kaupunki, _maakoodi = _parts
                    elif len(_parts) == 5:
                        _tarkenne = None
                        _nimi, _katuosoite, _postinumero, _kaupunki, _maakoodi = _parts
                # 18
                if delivery_address != '':
                    self.assertTrue(len(delivery_address) <= 255)
                    _parts = delivery_address.split("\\")
                    if len(_parts) == 6:
                        _nimi, _tarkenne, _katuosoite, _postinumero, _kaupunki, _maakoodi = _parts
                    elif len(_parts) == 5:
                        _tarkenne = None
                        _nimi, _katuosoite, _postinumero, _kaupunki, _maakoodi = _parts
                # 19
                if bill_notes_public != '':
                    self.assertTrue(len(bill_notes_public) <= 500)
                # 20
                if bill_notes_private != '':
                    self.assertTrue(len(bill_notes_private) <= 500)
                # 21
                if email_address != '':
                    self.assertTrue('@' in email_address)
                    self.assertTrue(len(email_address) <= 80)
                # 22
                if payment_date != '':
                    payment_date = datetime.strptime(bill_date, "%d.m.%Y")
                # 23
                if currency_rate != '':
                    float(currency_rate)
                # 24
                self.assertTrue(len(bill_amount) > 0, "Bill total amount non-empty")
                bill_amount = float(bill_amount)
                # 25
                if vat_percentage != '':
                    int(vat_percentage)
                # 26
                if billing_channel != '':
                    self.assertTrue(billing_channel in ['1', '2', '3', '6'],
                                    "Billing channel type known integer")
                else:
                    billing_channel = None
                # 27
                if billing_channel == '3':  # Verkkolasku
                    self.assertTrue(len(e_bill_id) > 0)
                # 28
                self.assertTrue(len(order_reference) <= 255)
                # 29
                if book_by_rows_code != '':
                    self.assertTrue(book_by_rows_code in ['t', 'f'])
                # 30, 31
                self.assertEqual(deprecated_1, '', "Legacy columns, empty")
                self.assertEqual(deprecated_2, '', "Legacy columns, empty")
                # 32
                if customer_id != '':
                    self.assertTrue(len(customer_id) <= 40)
                # 33
                if automatic_billing_code != '':
                    self.assertTrue(automatic_billing_code in ['X', 'M'])
                # 34
                self.assertEquals(attachment_file_name, '', 'Attachments not supported')
                # 35
                if contact_person != '':
                    self.assertTrue(len(contact_person) < 255)
                # 36
                if payment_type == 'ulkomaanmaksu' or other_party_swift != '':
                    self.assertTrue(8 <= len(other_party_swift) <= 11)
                # 37, 38
                if billing_channel == '3' or other_party_ovt:
                    self.assertTrue(12 <= len(other_party_ovt) <= 17)
                    self.assertTrue(e_bill_operator)
                # 39
                self.assertTrue(billing_id)
                # 40 factoring financing ignored
                # 41
                self.assertEqual(vat_country_code, '')
                # 42
                if language_code != '':
                    self.assertTrue(language_code in ['1', '2', '3', '4'])
                # 43
                if cash_discount_days != '':
                    self.assertEqual(cash_discount_days, '0')
                # 44
                if cash_discount_percentage != '':
                    self.assertEqual(cash_discount_percentage, '0')


                # Specific checks
                current_bill_id = billing_id
                if cancel_bill_code == 't':
                    # bill
                    self.assertIsNone(bill_amounts.get(billing_id),
                                      "Same bill id occurs twice")
                    self.assertTrue(float(bill_amount) > 0, "Total amount is positive")
                    bill_amounts[current_bill_id] = bill_amount
                else:
                    # cancel bill
                    self.assertTrue(float(bill_amount) < 0, "Total amount is negative")
                self.assertEquals(billing_channel, '6', "Billing channel is 6: do not send")
                self.assertTrue(Bill.objects.filter(id=int(current_bill_id)).exists(),
                                "Bill for bill ID exists")
            else:
                # Laskurivitietue
                (
                    empty,                      # 1
                    product_description,        # 2
                    product_code,               # 3
                    unit_count,                 # 4
                    unit_type,                  # 5
                    unit_price,                 # 6
                    discount_percentage,        # 7
                    vat_percentage,             # 8
                    line_comment,               # 9
                    order_reference,            # 10
                    customer_order_reference,   # 11
                    order_confirmation,         # 12
                    shipping_list_number,       # 13
                    book_account                # 14
                ) = columns[:14]
                # 1
                self.assertEqual(empty, '')
                self.assertTrue(len(product_description) <= 80)
                self.assertTrue(len(product_code) <= 80)
                unit_count = float(unit_count)
                unit_price = float(unit_price)
                discount_percentage = float(discount_percentage)*0.01 if discount_percentage else 0
                vat_percentage = int(vat_percentage) if columns[8-1] else 0
                self.assertTrue(book_account in self.BOOK_ACCOUNTS)
                line_amount = unit_count * unit_price * (1.0-discount_percentage)
                if unit_count > 0:  # Ignore cancel bills
                    lineitem_totals[current_bill_id] = lineitem_totals.get(current_bill_id, 0.0) + line_amount
        items_for_wrong_bill = set(bill_amounts.keys()).difference(lineitem_totals.keys())
        self.assertEqual(len(items_for_wrong_bill), 0, "Line item bill IDs must match bill IDs")
        for bill_id, amount in bill_amounts.items():
            self.assertEqual(amount, lineitem_totals[bill_id])

    def test_procountor_csv_format_cancelled_bill(self):
        self.membership.dissociate(self.user)
        message = self.get_procountor_email()
        __, attach_content, __ = message.attachments[0]
        self.check_procountor_csv_format(attach_content)

    def test_send_cancelledbill_deleted_member(self):
        self.membership.request_dissociation(self.user)
        self.membership.dissociate(self.user)
        self.assertEquals(CancelledBill.objects.count(), 1)
        self.membership.delete_membership(self.user)
        makebills()
        result_csv = create_csv(mark_cancelled=True)
        self.assertEqual(len(result_csv.splitlines()), 4, "Creating cancelled bill csv failed")
        self.check_procountor_csv_format(result_csv)

    def test_send_cancelledbill_dissociated_member(self):
        self.membership.request_dissociation(self.user)
        self.membership.dissociate(self.user)
        self.assertEquals(CancelledBill.objects.count(), 1)
        makebills()
        result_csv = create_csv(mark_cancelled=True)
        self.assertEqual(len(result_csv.splitlines()), 4, "Creating cancelled bill csv failed")
        self.check_procountor_csv_format(result_csv)


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

    def test_billingcycle_is_cancelled(self):
        self.assertEqual(self.membership.billingcycle_set.first().is_cancelled(), False,
                         "Member billingcycle.is_cancelled didn't return False")
        self.membership.request_dissociation(self.user)
        self.membership.dissociate(self.user)
        self.assertEqual(self.membership.billingcycle_set.first().is_cancelled(), True,
                         "Member billingcycle.is_cancelled returned didn't return True")


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
        with open_test_data("csv-test.csv") as f:
            process_op_csv(f)

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

        with open_test_data("csv-test.csv") as f:
            process_op_csv(f)
        payment_count = Payment.objects.filter(~no_cycle_q).count()
        error = "The payment in the sample file should have matched"
        self.assertEqual(payment_count, 1, error)
        payment = Payment.objects.filter(billingcycle=self.cycle).latest("payment_day")
        cycle = BillingCycle.objects.get(pk=self.cycle.pk)
        self.assertEqual(cycle.reference_number, payment.reference_number)
        self.assertTrue(cycle.is_paid)

    def test_duplicate_payment(self):
        no_cycle_q = Q(billingcycle=None)

        with open_test_data("csv-test-duplicate.csv") as f:
            process_op_csv(f)
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
        with open_test_data("csv-future.csv") as f:
            self.assertRaises(PaymentFromFutureException, process_op_csv, f)

    def test_csv_header_processing(self):
        error = "Should fail on invalid header"
        with open_test_data("csv-invalid.csv") as f:
            self.assertRaises(RequiredFieldNotFoundException, process_op_csv, f)
        with open_test_data("csv-test.csv") as f:
            process_op_csv(f)  # Valid csv should not raise header error


class ProcountorCSVNoMembersTest(TestCase):
    fixtures = ['membership_fees.json', 'test_user.json']

    def test_file_reading(self):
        "csvbills: test data should have 3 payments, none of which match"
        with open_test_data("procountor-csv-test.csv") as f:
            process_procountor_csv(f)

        payment_count = Payment.objects.count()
        error = "There should be 3 non-negative payments in the testdata"
        self.assertEqual(payment_count, 3, error)

        no_cycle_q = Q(billingcycle=None)
        nomatch_payments = Payment.objects.filter(~no_cycle_q).count()
        error = "No payments should match without any members in db"
        self.assertEqual(nomatch_payments, 0, error)

class ProcountorCSVReadingTest(TestCase):
    fixtures = ['membership_fees.json', 'test_user.json']

    def setUp(self):
        self.user = User.objects.get(id=1)
        membership = create_dummy_member('N', mid=11)
        membership.preapprove(self.user)
        membership.approve(self.user)
        cycle_start = datetime(2014, 9, 6)
        self.cycle = BillingCycle(membership=membership, start=cycle_start)
        self.cycle.save()
        self.bill = Bill(billingcycle=self.cycle)
        self.bill.save()

    def test_import_data(self):
        no_cycle_q = Q(billingcycle=None)

        with open_test_data("procountor-csv-test.csv") as f:
            process_procountor_csv(f)
        payment_count = Payment.objects.filter(~no_cycle_q).count()
        error = "The payment in the sample file should have matched"
        self.assertEqual(payment_count, 1, error)
        payment = Payment.objects.filter(billingcycle=self.cycle).latest("payment_day")
        cycle = BillingCycle.objects.get(pk=self.cycle.pk)
        self.assertEqual(cycle.reference_number, payment.reference_number)
        self.assertTrue(cycle.is_paid)

    def test_duplicate_payment(self):
        no_cycle_q = Q(billingcycle=None)

        with open_test_data("procountor-csv-duplicate.csv") as f:
            process_procountor_csv(f)
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
        with open_test_data("procountor-csv-future.csv") as f:
            self.assertRaises(PaymentFromFutureException, process_procountor_csv, f)

    def test_csv_header_processing(self):
        error = "Should fail on invalid header"
        with open_test_data("procountor-csv-invalid.csv") as f:
            self.assertRaises(RequiredFieldNotFoundException, process_procountor_csv, f)
        with open_test_data("procountor-csv-test.csv") as f:
            try:
                process_procountor_csv(f)
            except RequiredFieldNotFoundException:
                self.fail("Valid csv should not raise header error.")


class LoginRequiredTest(TestCase):
    fixtures = ['membership_fees.json', 'test_user.json']

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


class ContactTest(TestCase):

    def test_short_homepage(self):
        c = Contact(first_name="Aa", given_names="Aa", last_name="Bb")
        c.homepage = "www.kapsi.fi"
        c.save()
        self.assertEqual(c.homepage, "http://www.kapsi.fi")

    def test_short_homepage_create(self):
        c = Contact.objects.create(first_name="Aa", given_names="Aa",
            last_name="Bb", homepage = "www.kapsi.fi")
        c = Contact.objects.get(pk=c.pk)
        self.assertEqual(c.homepage, "http://www.kapsi.fi")

    def test_proper_homepage(self):
        c = Contact(first_name="Aa", given_names="Aa", last_name="Bb")
        c.homepage = "http://www.kapsi.fi"
        c.save()
        self.assertEqual(c.homepage, "http://www.kapsi.fi")

    def test_proper_secure_homepage(self):
        c = Contact(first_name="Aa", given_names="Aa", last_name="Bb")
        c.homepage = "https://www.kapsi.fi"
        c.save()
        self.assertEqual(c.homepage, "https://www.kapsi.fi")

class JuniorMemberApplicationTest(TestCase):
    fixtures = ['membership_fees.json', 'test_user.json']

    def setUp(self):
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
            "birth_year": "1993",
            "email_forward": "y.aikas",
            "mysql_database": "yes",
            "postgresql_database": "yes",
            "login_vhost": "yes",
    }

    def test_do_application_is_junior_1(self):
        post_data = dict(self.post_data)  # Copy data
        post_data['birth_year'] = str(datetime.now().year - 1)
        response = self.client.post('/membership/application/person/', post_data)
        self.assertRedirects(response, '/membership/application/person/success/')
        new = Membership.objects.latest("id")
        self.assertEquals(new.type, u"J")

    def test_do_application_is_junior_20(self):
        post_data = dict(self.post_data)  # Copy data
        post_data['birth_year'] = str(datetime.now().year - 20)
        response = self.client.post('/membership/application/person/', post_data)
        self.assertRedirects(response, '/membership/application/person/success/')
        new = Membership.objects.latest("id")
        self.assertEquals(new.type, u"J")

    def test_do_application_not_junior(self):
        post_data = dict(self.post_data)  # Copy data
        post_data['birth_year'] = str(datetime.now().year - 21)
        response = self.client.post('/membership/application/person/', post_data)
        self.assertRedirects(response, '/membership/application/person/success/')
        new = Membership.objects.latest("id")
        self.assertEquals(new.type, u"P")

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
            "birth_year": "1993",
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


    def test_do_application_with_short_homepage(self):
        self.post_data['homepage'] = 'www.kapsi.fi'
        response = self.client.post('/membership/application/person/', self.post_data)
        self.assertRedirects(response, '/membership/application/person/success/')
        new = Membership.objects.latest("id")
        self.assertEquals(new.person.homepage, u"http://www.kapsi.fi")

    def test_do_application_with_empty_phone_number(self):
        self.post_data['phone'] = ''
        response = self.client.post('/membership/application/person/', self.post_data)
        self.assertEquals(response.status_code, 200)
        self.assertFormError(response, 'form', 'phone', _('This field is required.'))

    def test_do_application_with_empty_sms_number(self):
        self.post_data['sms'] = ''
        response = self.client.post('/membership/application/person/', self.post_data)
        self.assertEquals(response.status_code, 200)
        self.assertFormError(response, 'form', 'sms', _('This field is required.'))

    def test_do_application_with_proper_homepage(self):
        self.post_data['homepage'] = 'http://www.kapsi.fi'
        response = self.client.post('/membership/application/person/', self.post_data)
        self.assertRedirects(response, '/membership/application/person/success/')
        new = Membership.objects.latest("id")
        self.assertEquals(new.person.homepage, u"http://www.kapsi.fi")

    def test_do_application_with_proper_secure_homepage(self):
        self.post_data['homepage'] = 'https://www.kapsi.fi'
        response = self.client.post('/membership/application/person/', self.post_data)
        self.assertRedirects(response, '/membership/application/person/success/')
        new = Membership.objects.latest("id")
        self.assertEquals(new.person.homepage, u"https://www.kapsi.fi")

    def test_redundant_email_alias(self):
        self.post_data['unix_login'] = 'fnamelname'
        self.post_data['email_forward'] = 'fname.lname'
        response = self.client.post('/membership/application/person/', self.post_data)
        self.assertRedirects(response, '/membership/application/person/success/')
        new = Membership.objects.latest("id")
        self.assertEquals(new.person.first_name, u"Yrjö")

    def test_clean_ajax_output(self):
        post_data = self.post_data.copy()
        post_data['first_name'] = u'<b>Yrjö</b>'
        post_data['extra_info'] = '<iframe src="https://www.kapsi.fi" width=200 height=100></iframe>'
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
                         '&lt;iframe src=&quot;https://www.kapsi.fi&quot; width=200 height=100&gt;&lt;/iframe&gt;')


    def _validate_alias(self, alias):
        json_response = self.client.post('/membership/application/handle_json/',
            json.dumps({"requestType": "VALIDATE_ALIAS", "payload": alias}),
                       content_type="application/json")
        self.assertEqual(json_response.status_code, 200)
        json_dict = json.loads(json_response.content)
        return json_dict

    def test_validate_alias_ajax(self):
        m = create_dummy_member('A')
        m.save()
        alias = Alias(name='validalias', owner=m)
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

class OrganizationRegistratioTest(TestCase):
    def setUp(self):
        self.field = OrganizationRegistrationNumber()

    def test_valid(self):
        self.assertEqual(u"1.11", self.field.clean(u"1.11"))
        self.assertEqual(u"123.123", self.field.clean(u"123.123"))

    def test_invalid(self):
        self.assertRaises(ValidationError, self.field.clean, "str.str")
        self.assertRaises(ValidationError, self.field.clean, "11111")
        self.assertRaises(ValidationError, self.field.clean, "11111.1111111")

class LoginFieldTest(TestCase):
    def setUp(self):
        self.field = LoginField()

    def test_valid(self):
        self.assertEquals(u"testuser", self.field.clean(u"testuser"))
        self.assertEquals(u"testuser2", self.field.clean(u"testuser2"))
        self.assertEquals(u"a1b2c4", self.field.clean(u"a1b2c4"))
    def test_uppercase(self):
        self.assertEquals(u"testuser", self.field.clean(u"TestUser"))

    def test_bad_chars(self):
        self.assertRaises(ValidationError, self.field.clean, "user.name")
        self.assertRaises(ValidationError, self.field.clean, "user-name")


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
        login = self.client.login(username='admin', password='dhtn')
        self.failUnless(login, 'Could not log in')

    def test_renders_member_id(self):
        response = self.client.get('/membership/memberships/approved/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('<span class="member_id">#%i</span>' % self.m1.id in response.content)

        response = self.client.get('/membership/memberships/preapproved/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('<span class="member_id">#%i</span>' % self.m2.id in response.content)

        response = self.client.get('/membership/memberships/new/')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('<li class="list_item preapprovable" id="%i">' % self.m3.id in response.content)

    def test_memberlist_pagination(self):
        response = self.client.get('/membership/memberships/approved/?page=1')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('<span class="member_id">#%i</span>' % self.m1.id in response.content)

        response = self.client.get('/membership/memberships/approved/?page=2')
        self.assertEqual(response.status_code, 404)

    def test_memberlist_sort_by_name(self):
        response = self.client.get('/membership/memberships/approved/?sort=name')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('<span class="member_id">#%i</span>' % self.m1.id in response.content)

    def test_memberlist_sort_by_id(self):
        response = self.client.get('/membership/memberships/approved/?sort=id')
        self.assertEqual(response.status_code, 200)
        self.assertTrue('<span class="member_id">#%i</span>' % self.m1.id in response.content)


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


class MemberDissociationRequestedTest(TestCase):
    fixtures = ['membership_fees.json', 'test_user.json']

    def setUp(self):
        self.user = User.objects.get(id=1)

    def test_application_request_dissociation(self):
        m = create_dummy_member('N')
        self.assertRaises(MembershipOperationError, m.request_dissociation, self.user)

    def test_preapproved_request_dissociation(self):
        m = create_dummy_member('N')
        m.preapprove(self.user)
        self.assertRaises(MembershipOperationError, m.request_dissociation, self.user)

    def test_preapprove_twice(self):
        m = create_dummy_member('N')
        m.preapprove(self.user)
        self.assertRaises(MembershipOperationError, m.preapprove, self.user)

    def test_approved_request_dissociation(self):
        m = create_dummy_member('N')
        m.preapprove(self.user)
        m.approve(self.user)

        self.assertIsNone(m.dissociation_requested)
        before = datetime.now()
        m.request_dissociation(self.user)
        after = datetime.now()

        self.assertIsNotNone(m.dissociation_requested)
        self.assertTrue(m.dissociation_requested > before)
        self.assertTrue(m.dissociation_requested < after)

    def test_approved_request_dissociate_delete(self):
        m = create_dummy_member('N')
        m.preapprove(self.user)
        m.approve(self.user)
        m.request_dissociation(self.user)
        m.dissociate(self.user)
        m.delete_membership(self.user)

    def test_disassociation_cancels_outstanding_bills_db(self):
        m = create_dummy_member('N')
        m.preapprove(self.user)
        m.approve(self.user)
        makebills()
        m.request_dissociation(self.user)
        self.assertEquals(CancelledBill.objects.count(), 0)
        m.dissociate(self.user)
        self.assertEquals(CancelledBill.objects.count(), 1,
                          "Outstanding bills are cancelled")

    def test_disassociation_cancels_outstanding_bills_logging(self):
        handler = MockLoggingHandler()
        models_logger.addHandler(handler)

        m = create_dummy_member('N')
        m.preapprove(self.user)
        m.approve(self.user)
        makebills()
        m.request_dissociation(self.user)
        m.dissociate(self.user)

        canceled_msg = 'Created CancelledBill for Member'
        message_logged = any([canceled_msg in x for x in handler.messages['info']])
        self.assertTrue(message_logged)
        makebills_logger.removeHandler(handler)

    def test_approved_request_dissociate_delete_twice(self):
        m = create_dummy_member('N')
        m.preapprove(self.user)
        m.approve(self.user)
        m.request_dissociation(self.user)
        m.dissociate(self.user)
        m.delete_membership(self.user)
        self.assertRaises(MembershipAlreadyStatus, m.delete_membership, self.user)

    def test_dissociated_request_dissociation(self):
        m = create_dummy_member('N')
        m.preapprove(self.user)
        m.approve(self.user)
        m.request_dissociation(self.user)
        m.dissociate(self.user)
        self.assertRaises(MembershipOperationError, m.request_dissociation, self.user)


class MemberCancelDissociationRequestTest(TestCase):
    fixtures = ['membership_fees.json', 'test_user.json']
    def setUp(self):
        self.user = User.objects.get(id=1)

    def test_application_request_dissociation(self):
        m = create_dummy_member('N')
        self.assertRaises(MembershipOperationError, m.cancel_dissociation_request, self.user)

    def test_preapproved_request_dissociation(self):
        m = create_dummy_member('N')
        m.preapprove(self.user)
        self.assertRaises(MembershipOperationError, m.cancel_dissociation_request, self.user)

    def test_approved_request_cancel_dissociation_before_dissociation(self):
        m = create_dummy_member('N')
        m.preapprove(self.user)
        m.approve(self.user)
        self.assertRaises(MembershipOperationError, m.cancel_dissociation_request, self.user)

    def test_approved_request_dissociation(self):
        m = create_dummy_member('N')
        m.preapprove(self.user)
        m.approve(self.user)
        m.request_dissociation(self.user)
        m.cancel_dissociation_request(self.user)
        self.assertIsNone(m.dissociation_requested)

    def test_dissociated_request_dissociation(self):
        m = create_dummy_member('N')
        m.preapprove(self.user)
        m.approve(self.user)
        m.request_dissociation(self.user)
        m.dissociate(self.user)
        self.assertRaises(MembershipOperationError, m.cancel_dissociation_request, self.user)

class MemberDissociationTest(TestCase):
    fixtures = ['membership_fees.json', 'test_user.json']
    def setUp(self):
        self.user = User.objects.get(id=1)

    def test_application_dissociation(self):
        m = create_dummy_member('N')
        self.assertRaises(MembershipOperationError, m.dissociate, self.user)

    def test_preapproved_dissociation(self):
        m = create_dummy_member('N')
        m.preapprove(self.user)
        self.assertRaises(MembershipOperationError, m.dissociate, self.user)

    def test_dissociation_request_dissociation(self):
        m = create_dummy_member('N')
        m.preapprove(self.user)
        m.approve(self.user)
        m.request_dissociation(self.user)
        m.dissociate(self.user)

    def test_approved_dissociation(self):
        m = create_dummy_member('N')
        m.preapprove(self.user)
        m.approve(self.user)

        self.assertIsNone(m.dissociated)
        before = datetime.now()
        m.dissociate(self.user)
        after = datetime.now()

        self.assertIsNotNone(m.dissociated)
        self.assertTrue(m.dissociated > before)
        self.assertTrue(m.dissociated < after)


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
    return HttpResponse('OK', content_type='text/plain')

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
        m1.person.first_name = "Aino"
        m1.person.save()

        m2 = create_dummy_member('N')
        m2.save()
        m2.person.last_name = m1.person.last_name
        m2.person.first_name = "Esko"
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

    def test_empty_phone_is_not_duplicate(self):
        m1 = create_dummy_member('N')
        m1.save()
        m1.person.phone = ''
        m1.person.save()

        m2 = create_dummy_member('N')
        m2.save()
        m2.person.phone = ''
        m2.person.save()

        self.assertEquals(len(m1.duplicates()), 0)


class MembershipSearchTest(TestCase):
    def setUp(self):
        self.m = create_dummy_member('N')
        self.m.save()

        self.o = create_dummy_member('N', type='O')
        self.o.save()

    def test_find_by_first_name(self):
        self.assertEquals(len(Membership.search(self.m.person.first_name)), 1)

    def test_find_by_last_name(self):
        self.assertEquals(len(Membership.search(self.m.person.last_name)), 1)

    def test_find_by_organization_name(self):
        self.assertEquals(len(Membership.search(self.o.organization.organization_name)), 1)

    def test_find_by_membership_id(self):
        self.assertEquals(len(Membership.search("#{id}".format(id=self.m.id))), 1)

    def test_find_by_membership_id_org(self):
        self.assertEquals(len(Membership.search("#{id}".format(id=self.o.id))), 1)

    def test_find_by_membership_id_does_not_exist(self):
        self.assertEquals(len(Membership.search("#{id}".format(id=12765))), 0)

    def test_find_by_alias(self):
        alias = Alias(owner=self.m,
                      name=u"this.alias.should.be.unique")
        alias.save()
        self.assertEquals(len(Membership.search(alias.name)), 1)


class MembershipPaperReminderSentTest(TestCase):
    fixtures = ['membership_fees.json', 'test_user.json']

    def setUp(self):
        self.user = User.objects.get(id=1)

        self.m = create_dummy_member('N')
        self.m.save()
        self.m.preapprove(self.user)
        self.m.approve(self.user)

        self.m2 = create_dummy_member('N')
        self.m2.save()
        self.m2.preapprove(self.user)
        self.m2.approve(self.user)

        self.m3 = create_dummy_member('N')
        self.m3.save()
        self.m3.preapprove(self.user)
        self.m3.approve(self.user)

        self.m4 = create_dummy_member('N')
        self.m4.save()
        self.m4.preapprove(self.user)
        self.m4.approve(self.user)

        # Positive #1
        cycle_start = datetime.now() - timedelta(days=60)
        cycle = BillingCycle(membership=self.m, start=cycle_start)
        cycle.save()
        bill = Bill(billingcycle=cycle, type='P',
                    due_date=datetime.now() - timedelta(days=20))
        bill.save()

        # Positive #2
        cycle_start = datetime.now() - timedelta(days=60)
        cycle = BillingCycle(membership=self.m2, start=cycle_start)
        cycle.save()
        bill = Bill(billingcycle=cycle, type='P',
                    due_date=datetime.now() - timedelta(days=10))
        bill.save()

        # Negative #1
        cycle_start = datetime.now() - timedelta(days=60)
        cycle = BillingCycle(membership=self.m3, start=cycle_start)
        cycle.save()
        bill = Bill(billingcycle=cycle,
                    due_date=datetime.now() - timedelta(days=20))
        bill.save()

        # Negative #2
        cycle_start = datetime.now() - timedelta(days=60)
        cycle = BillingCycle(membership=self.m4, start=cycle_start)
        cycle.save()
        bill = Bill(billingcycle=cycle, type='P',
                    due_date=datetime.now() - timedelta(days=5))
        bill.save()


    def test_membership_found_for_late_paper_reminder(self):
        qs = Membership.paper_reminder_sent_unpaid_after()
        self.assertEquals(1, len(qs))
        self.assertIn(self.m, qs)

        qs = Membership.paper_reminder_sent_unpaid_after(days=9)
        self.assertEquals(2, len(qs))
        self.assertIn(self.m, qs)
        self.assertIn(self.m2, qs)


class CorrectVatAmountInBillTest(TestCase):
    """
    Test with cycle starting in 2013 and 2014. 2013 should have VAT 0% while
    2013 24%.

    SingleMemberBillingTest has an example of how to catch e-mails.
    """
    fixtures = ['membership_fees.json', 'test_user.json']

    def setUp(self):
        #settings.BILLING_CC_EMAIL = None
        self.user = User.objects.get(id=1)

        self.m = create_dummy_member('N')
        self.m.save()
        self.m.preapprove(self.user)
        self.m.approve(self.user)

        cycle_start = datetime(year=2012, month=10, day=10)
        self.cycle = BillingCycle(membership=self.m, start=cycle_start)
        self.cycle.save()
        cycle_start_2014 = datetime(year=2014, month=1, day=10)
        self.cycle_2014 = BillingCycle(membership=self.m,
                                       start=cycle_start_2014)
        self.cycle_2014.save()
        self.bill_2013 = Bill(billingcycle=self.cycle, type='P',
                         due_date=cycle_start)
        self.bill_2014 = Bill(billingcycle=self.cycle_2014, type='P',
                         due_date=cycle_start_2014)
        #mail.outbox = []

    def tearDown(self):

        #self.bill_2014.delete()
        #self.bill_2013.delete()
        self.cycle.delete()
        self.cycle_2014.delete()
        self.m.delete()

    def test_should_contain_vat_percentage(self):
        self.assertIn("vero 24", self.bill_2014.render_as_text())

    def test_should_not_contain_vat_percentage(self):
        self.assertNotIn("vero 24", self.bill_2013.render_as_text())


class EmailUtilsTests(TestCase):
    def test_unicode_in_name(self):
        res = email_utils.format_email(u'räyh', 'foo@bar')
        self.assertEqual(res, u'"räyh" <foo@bar>')

    def test_clean_ascii_name(self):
        res = email_utils.format_email('rauh', 'foo@bar')
        self.assertEqual(res, u'"rauh" <foo@bar>')

    def test_comma_in_name(self):
        res = email_utils.format_email('rauh,joo', 'foo@bar')
        self.assertEqual(res, u'"rauh,joo" <foo@bar>')

    def test_semicolon_in_name(self):
        res = email_utils.format_email('rauh;joo', 'foo@bar')
        self.assertEqual(res, u'"rauh;joo" <foo@bar>')

    def test_dquote_in_name(self):
        res = email_utils.format_email('rauh\"joo', 'foo@bar')
        self.assertEqual(res, u'"rauhjoo" <foo@bar>')

    def test_quote_in_name(self):
        res = email_utils.format_email('rauh\'joo', 'foo@bar')
        self.assertEqual(res, u'"rauh\'joo" <foo@bar>')
