# -*- coding: utf-8 -*-

import logging
from datetime import datetime, timedelta
from random import randint

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase

from models import *
from utils import *
from test_utils import *

from reference_numbers import *

from management.commands.makebills import Command as makebills_command
from management.commands.makebills import membership_approved_time
from management.commands.makebills import create_billingcycle
from management.commands.makebills import send_reminder
from management.commands.makebills import NoApprovedLogEntry

class ReferenceNumberTest(TestCase):
    def test_1234(self):
        self.failUnlessEqual(generate_checknumber("1234"), 4)
    def test_1234_add(self):
        self.assertEqual(add_checknumber("1234"), "12344")
    def test_666666_add(self):
        self.assertEqual(add_checknumber("666666"), "6666668")

    def test_uniqueness_of_reference_numbers(self):
        numbers = set([])
        for i in xrange(1, 10000):
            for j in xrange(datetime.now().year, datetime.now().year + 11):
                number = generate_membership_bill_reference_number(i, j)
                self.assertFalse(number in numbers)
                numbers.add(number)


def create_dummy_member(status):
    if status not in ['N', 'P', 'A']:
        raise Error("Unknown membership status")
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
    membership = Membership(type='P', status=status,
                            person=person,
                            nationality='Finnish',
                            municipality='Paska kaupunni',
                            extra_info='Hintsunlaisesti semmoisia tietoja.')
    logging.info("New application %s from %s:." % (str(person), '::1'))
    membership.save()
    return membership


class BillingTest(TestCase):
    # http://docs.djangoproject.com/en/dev/topics/testing/#fixture-loading
    fixtures = ['membership_fees.json', 'test_user.json']
    #
    # http://docs.djangoproject.com/en/dev/topics/testing/#django.core.mail.django.core.mail.outbox

    # NOTE: also make sure billing addresses are correct
    def test_single_preapproved_no_op(self):
        "makebills: preapproved membership no-op"
        membership = create_dummy_member('N')
        membership.preapprove()
        c = makebills_command()
        c.handle_noargs()
        
        self.assertEqual(len(mail.outbox), 0)
        cycles = membership.billingcycle_set.all()
        self.assertEqual(len(cycles), 0)

    def test_membership_approved_time_no_entries(self):
        "makebills: approved_time with no entries"
        membership = create_dummy_member('N')
        membership.preapprove()
        membership.status = 'A'
        membership.save()
        self.assertRaises(NoApprovedLogEntry, membership_approved_time, membership)

    def test_membership_approved_time_multiple_entries(self):
        "makebills: approved_time multiple entries"
        user = User.objects.get(id=1)
        membership = create_dummy_member('N')
        membership.preapprove()
        membership.approve()
        log_change(membership, user, change_message="Approved")
        log_change(membership, user, change_message="Approved")
        approve_entries = membership.logs.filter(change_message="Approved").order_by('-action_time')
        
        t = membership_approved_time(membership)
        self.assertEquals(t, approve_entries[0].action_time)

    def test_bill_is_reminder(self):
        "models.bill.is_reminder()"
        user = User.objects.get(id=1)
        membership = create_dummy_member('N')
        membership.preapprove()
        membership.approve()
        log_change(membership, user, change_message="Approved")

        cycle = create_billingcycle(membership)
        reminder_bill = send_reminder(membership)
        first_bill = Bill.objects.filter(billingcycle=cycle).order_by('due_date')[0]

        self.assertTrue(reminder_bill.is_reminder())
        self.assertFalse(first_bill.is_reminder())

    def test_billing_cycle_last_bill(self):
        "models.Bill.last_bill()"
        user = User.objects.get(id=1)
        membership = create_dummy_member('N')
        membership.preapprove()
        membership.approve()
        log_change(membership, user, change_message="Approved")

        cycle = create_billingcycle(membership)
        reminder_bill = send_reminder(membership)
        first_bill = Bill.objects.filter(billingcycle=cycle).order_by('due_date')[0]

        last_bill = cycle.bill_set.order_by("-due_date")[0]
        self.assertEquals(last_bill.id, reminder_bill.id)
        self.assertNotEquals(last_bill.id, first_bill.id)

    def test_billing_cycle_is_last_bill_late(self):
        "models.Bill.is_last_bill_late()"
        user = User.objects.get(id=1)
        membership = create_dummy_member('N')
        membership.preapprove()
        membership.approve()
        log_change(membership, user, change_message="Approved")

        cycle = create_billingcycle(membership)
        first_bill = Bill.objects.filter(billingcycle=cycle).order_by('due_date')[0]
        last_bill = cycle.bill_set.order_by("-due_date")[0]

        self.assertTrue(datetime.now() + timedelta(days=15) > last_bill.due_date)

    def test_approved_cycle_and_bill_creation(self):
        "makebills: cycle and bill creation"
        user = User.objects.get(id=1)
        membership = create_dummy_member('N')
        membership.preapprove()
        membership.approve()
        log_change(membership, user, change_message="Approved")
        c = makebills_command()
        c.handle_noargs()

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(len(membership.billingcycle_set.all()), 1)

        membership2 = create_dummy_member('N')
        membership2.preapprove()
        membership2.approve()
        log_change(membership2, user, change_message="Approved")

        c.handle_noargs()

        self.assertEqual(len(membership2.billingcycle_set.all()), 1)
        self.assertEqual(len(mail.outbox), 2)

    def test_expiring_cycles(self):
        print "test_expiring_cycles not implemented"
        # TODO:
        #  - create memberships:
        #    - one with more than a month to go on their cycle
        #    - one with less than a month to go
        #    - one whose cycle has ended already and no bill has been sent
        #      (the system should throw an error when handling this (should never happen))
        # c = makebills_command()
        # c.handle_noargs({})
        # Handle these cases accordingly, focus on the changes in the
        # database, e-mail sending is handled elsewhere.
    def test_bill_sending(self):
        print "test_bill_sending not implemented"
        # TODO:
        #  - create memberships:
        #    - one with less than a month to go (so as to trigger a bill)
        #    - one with more than a month to go (a bill should not be sent)
        #    - one whose cycle has ended already and no bill has been sent
        #      (the system should throw an error when handling this (should never happen))
        # c = makebills_command()
        # c.handle_noargs({})

    def test_new_billing_cycle_with_existing(self):
        "makebills: new billing cycle with existing cycles present"
        user = User.objects.get(id=1)
        c = makebills_command()
        
        m1 = create_dummy_member('N')
        m1.preapprove()
        m1.approve()
        log_change(m1, user, change_message="Approved")
        
        c.handle_noargs()
        self.assertEqual(len(m1.billingcycle_set.all()), 1)
        
        m2 = create_dummy_member('N')
        m2.preapprove()
        m2.approve()
        log_change(m2, user, change_message="Approved")
        
        c.handle_noargs()
        self.assertEqual(len(m2.billingcycle_set.all()), 1)

        yesterday = datetime.now() - timedelta(days=1)
        bc2 = m2.billingcycle_set.all()[0]
        bc2.end = yesterday
        bc2.save()
        b2 = bc2.last_bill()
        b2.due_date = yesterday
        b2.save()

        c.handle_noargs()
        self.assertTrue(len(m2.billingcycle_set.all()), 2)
        self.assertEqual(len(mail.outbox), 3)
