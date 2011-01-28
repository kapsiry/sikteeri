# -*- coding: utf-8 -*-

import os
import tempfile
import logging
logger = logging.getLogger("tests")

from datetime import datetime, timedelta
from random import randint
import simplejson

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase

from models import *
from utils import *
from test_utils import *

from reference_numbers import generate_membership_bill_reference_number
from reference_numbers import generate_checknumber, add_checknumber

from management.commands.makebills import logger as makebills_logger
from management.commands.makebills import makebills
from management.commands.makebills import membership_approved_time
from management.commands.makebills import create_billingcycle
from management.commands.makebills import send_reminder
from management.commands.makebills import can_send_reminder
from management.commands.makebills import NoApprovedLogEntry

from management.commands.csvbills import process_csv

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

    def test_uniqueness_of_reference_numbers(self):
        numbers = set([])
        for i in xrange(1, 100):
            for j in xrange(datetime.now().year, datetime.now().year + 11):
                number = generate_membership_bill_reference_number(i, j)
                self.assertFalse(number in numbers)
                numbers.add(number)


def create_dummy_member(status, type='P', mid=None):
    if status not in ['N', 'P', 'A']:
        raise Error("Unknown membership status")
    if type not in ['P', 'S', 'O', 'H']:
        raise Error("Unknown membership type")
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
    person = Contact(**d)
    person.save()
    if type == 'O':
        membership = Membership(id=mid, type=type, status=status,
                                organization=person,
                                nationality='Finnish',
                                municipality='Paska kaupunni',
                                extra_info='Hintsunlaisesti semmoisia tietoja.')
    else:
        membership = Membership(id=mid, type=type, status=status,
                                person=person,
                                nationality='Finnish',
                                municipality='Paska kaupunni',
                                extra_info='Hintsunlaisesti semmoisia tietoja.')
    logger.info("New application %s from %s:." % (str(person), '::1'))
    membership.save()
    return membership

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

    def tearDown(self):
        pass

    def test_single_preapproved_no_op(self):
        "makebills: preapproved membership no-op"
        membership = create_dummy_member('N')
        membership.preapprove(self.user)
        makebills()
        
        self.assertEqual(len(mail.outbox), 0)
        cycles = membership.billingcycle_set.all()
        self.assertEqual(len(cycles), 0)
        membership.delete()

    def test_membership_approved_time_no_entries(self):
        "makebills: approved_time with no entries"
        membership = create_dummy_member('N')
        membership.status = 'A'
        membership.save()

        handler = MockLoggingHandler()
        makebills_logger.addHandler(handler)
        self.assertRaises(NoApprovedLogEntry, membership_approved_time, membership)

        criticals = handler.messages["critical"]
        logged = False
        for critical in criticals:
            if "doesn't have Approved log entry" in critical:
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

        t = membership_approved_time(membership)
        self.assertEquals(t, approve_entries.latest("action_time").action_time)


class SingleMemberBillingTest(TestCase):
    # http://docs.djangoproject.com/en/dev/topics/testing/#fixture-loading
    fixtures = ['membership_fees.json', 'test_user.json']

    # http://docs.djangoproject.com/en/dev/topics/testing/#django.core.mail.django.core.mail.outbox

    def setUp(self):
        self.user = User.objects.get(id=1)
        membership = create_dummy_member('N')
        membership.preapprove(self.user)
        membership.approve(self.user)
        self.membership = membership

    def tearDown(self):
        self.membership.delete()

    def test_sending_no_cycle(self):
        makebills()
        self.assertEquals(len(mail.outbox), 1)

    def test_email_address_correct(self):
        makebills()
        self.assertEquals(self.membership.billing_email(), mail.outbox[0].to[0])

    def test_expired_cycle(self):
        "makebills: before a cycle expires, a new one is created"
        cycle = create_billingcycle(self.membership)
        cycle.starts = datetime.now() - timedelta(days=365)
        cycle.ends = datetime.now() + timedelta(days=27)
        cycle.save()

        makebills()

        self.assertEquals(len(mail.outbox), 1)

    def test_no_cycle_created(self):
        "makebills: no cycles after an expired membership, should log critical"
        m = self.membership
        makebills()

        c = m.billingcycle_set.all()[0]
        c.end = datetime.now() - timedelta(hours=1)
        c.save()

        handler = MockLoggingHandler()
        makebills_logger.addHandler(handler)
        makebills()
        makebills_logger.removeHandler(handler)

        criticals = handler.messages["critical"]
        self.assertTrue(len(criticals) > 0)
        
        logged = False
        for critical in criticals:
            if "no new billing cycle created for" in critical:
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

        makebills()

        self.assertEqual(len(membership2.billingcycle_set.all()), 1)
        self.assertEqual(len(mail.outbox), 2)

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
        self.assertFalse(self.bill.is_reminder())
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

    def test_can_send_reminder(self):
        handler = MockLoggingHandler()
        makebills_logger.addHandler(handler)
        now = datetime.now()
        can_send = can_send_reminder(now)
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
        can_send = can_send_reminder(two_weeks_ago)
        self.assertFalse(can_send, "Should fail if payment is old")
        criticals = len(handler.messages['critical'])
        self.assertEqual(criticals, 0, "No critical log messages, got %d" % criticals)
        makebills_logger.removeHandler(handler)

        p = Payment(billingcycle=self.cycle, amount=5, payment_day=now,
            transaction_id="test_can_send_reminder_2")
        p.save()
        can_send = can_send_reminder(month_ago)
        self.assertTrue(can_send, "Should be true with recent payment")

class CSVNoMembersTest(TestCase):
    fixtures = ['membership_fees.json', 'test_user.json']

    def test_file_reading(self):
        "csvbills: process_csv ran with no members"
        process_csv("../membership/fixtures/csv-test.txt")
        payment_count = Payment.objects.count()
        error = "No payments should match without any members"
        self.assertEqual(payment_count, 0, error)

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
        process_csv("../membership/fixtures/csv-test.txt")
        payment_count = Payment.objects.count()
        error = "The payment in the sample file should have matched"
        self.assertEqual(payment_count, 1, error)
        payment = Payment.objects.latest("payment_day")
        cycle = BillingCycle.objects.get(pk=self.cycle.pk)
        self.assertEqual(cycle.reference_number, payment.reference_number)
        self.assertTrue(cycle.is_paid)

class LoginRequiredTest(TestCase):
    fixtures = ['membpership_fees.json', 'test_user.json']

    def setUp(self):
        self.urls = ['/membership/memberships/new/',
                     '/membership/memberships/preapproved/',
                     '/membership/memberships/approved/',
                     '/membership/memberships/deleted/',
                     '/membership/memberships/',
                     '/membership/bills/unpaid/',
                     '/membership/bills/',
                     '/membership/payments/unknown/',
                     '/membership/payments/',
                     '/membership/testemail/',]

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

class MemberApplicationTest(TestCase):
    fixtures = ['membpership_fees.json', 'test_user.json']

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
            "extra_info": u"Mää oon testikäyttäjä."
        }

    def test_do_application(self):
        response = self.client.post('/membership/persons/application/', self.post_data)
        self.assertRedirects(response, '/membership/memberships/new/success/')
        new = Membership.objects.latest("id")
        self.assertEquals(new.person.first_name, u"Yrjö")

    def test_clean_ajax_output(self):
        post_data = self.post_data.copy()
        post_data['first_name'] = u'<b>Yrjö</b>'
        post_data['extra_info'] = '<iframe src="http://www.kapsi.fi" width=200 height=100></iframe>'
        response = self.client.post('/membership/persons/application/', post_data)
        self.assertRedirects(response, '/membership/memberships/new/success/')
        new = Membership.objects.latest("id")
        self.assertEquals(new.person.first_name, u"<b>Yrjö</b>")

        login = self.client.login(username='admin', password='dhtn')
        self.failUnless(login, 'Could not log in')
        json_response = self.client.post('/membership/memberships/handle_json/',
                                             simplejson.dumps({"requestType": "MEMBERSHIP_DETAIL", "payload": new.id}),
                                             content_type="application/json")
        self.assertEqual(json_response.status_code, 200)
        json_dict = simplejson.loads(json_response.content)
        self.assertEqual(json_dict['contacts']['person']['first_name'],
                         u'&lt;b&gt;Yrjö&lt;/b&gt;')
        self.assertEqual(json_dict['extra_info'],
                         '&lt;iframe src=&quot;http://www.kapsi.fi&quot; width=200 height=100&gt;&lt;/iframe&gt;')

