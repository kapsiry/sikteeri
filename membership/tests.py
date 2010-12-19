# -*- coding: utf-8 -*-

from datetime import datetime

from django.test import TestCase

from models import *
from utils import *

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


class BillingTest(TestCase):
    # http://docs.djangoproject.com/en/dev/topics/testing/#fixture-loading
    # fixtures = ['membership_fees.json', 'simple_billing.json']
    #
    # http://docs.djangoproject.com/en/dev/topics/testing/#django.core.mail.django.core.mail.outbox

    # How should we differentiate between approved, pre-approved etc?  These
    # are corner cases aswell and should be handled in different tests.
    
    # NOTE: also make sure billing addresses are correct
    
    def test_expiring_cycles(self):
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
        pass
    def test_bill_sending(self):
        # TODO:
        #  - create memberships:
        #    - one with less than a month to go (so as to trigger a bill)
        #    - one with more than a month to go (a bill should not be sent)
        #    - one whose cycle has ended already and no bill has been sent
        #      (the system should throw an error when handling this (should never happen))
        # c = makebills_command()
        # c.handle_noargs({})
        pass
    def test_reminder_sending(self):
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
        pass
