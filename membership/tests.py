# -*- coding: utf-8 -*-

import logging
from datetime import datetime
from random import randint

from django.core import mail
from django.test import TestCase

from models import *
from utils import *
from test_utils import *

from reference_numbers import *

from management.commands.makebills import Command as makebills_command


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
    # fixtures = ['membership_fees.json', 'simple_billing.json']
    #
    # http://docs.djangoproject.com/en/dev/topics/testing/#django.core.mail.django.core.mail.outbox

    # How should we differentiate between approved, pre-approved etc?  These
    # are corner cases aswell and should be handled in different tests.
    
    # NOTE: also make sure billing addresses are correct
    def test_single_preapproved_no_op(self):
        "Test preapproved membership: nothing should be created"
        membership = create_dummy_member('N')
        membership.preapprove()
        c = makebills_command()
        c.handle_noargs()
        
        self.assertEqual(len(mail.outbox), 0)
        cycles = membership.billingcycle_set.all()
        self.assertEqual(len(cycles), 0)

    def test_approved_cycle_and_bill_creation(self):
        "Test approved membership: cycle and bill creation"
        membership = create_dummy_member('N')
        membership.preapprove()
        membership.approve()
        c = makebills_command()
        c.handle_noargs()
        
        self.assertEqual(len(mail.outbox), 1)
        cycles = membership.billingcycle_set.all()
        self.assertEqual(len(cycles), 1)

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
    def test_reminder_sending(self):
        print "test_reminder_sending not implemented"
        # TODO:
        #  - populate database
        #    - a membership whose bill is overdue
        #    - a membership whose bill is not overdue
        #    - a membership who should be reminded again
        
        # How many times do we remind?  Should a special e-mail message be
        # sent to billing people once a certain count is reached?  Or is every
        # reminder already sent to billing?

        # c = makebills_command()
        # c.handle_noargs({})
