# -*- coding: utf-8 -*-
"""
generate_test_data.py

Copyright (c) 2010-2014 Kapsi Internet-käyttäjät ry. All rights reserved.
"""

from django.contrib.auth.models import User
from django.core import management
from django.core.management.base import BaseCommand
from django.db import transaction

from membership.models import Contact, Membership, Fee, Payment
from membership.billing.payments import attach_payment_to_cycle
from membership.reference_numbers import generate_membership_bill_reference_number
from membership.test_utils import random_first_name, random_last_name
from services.models import Alias, Service, ServiceType

from datetime import datetime
from decimal import Decimal
import logging
from random import random, randint, choice
import sys
from uuid import uuid4

logger = logging.getLogger("sikteeri.generate_test_data")


class Command(BaseCommand):
    help = 'Generate test random member data for development.'

    def add_arguments(self, parser):
        # Named (optional) arguments
        parser.add_argument('--approved',
                            type=int,
                            dest='approved',
                            default=100,
                            help='Number of approved members (100)')
        parser.add_argument('--preapproved',
                            type=int,
                            dest='preapproved',
                            default=20,
                            help='Number of preapproved members (20)')
        parser.add_argument('--new',
                            type=int,
                            dest='new',
                            default=15,
                            help='Number of new members (15)')

        parser.add_argument('--duplicates',
                            type=int,
                            dest='duplicates',
                            default=5,
                            help='Number of duplicate members (5)')
        parser.add_argument('--dissociated',
                            type=int,
                            dest='dissociated',
                            default=5,
                            help='Number of dissociated members (5)')
        parser.add_argument('--dissociation-requested',
                            type=int,
                            dest='dissociation_requested',
                            default=2,
                            help='Number of dissociation requested members (2)')
        parser.add_argument('--deleted',
                            type=int,
                            dest='deleted',
                            default=2,
                            help='Number of deleted members (2)')

    def handle(self, *args, **options):
        if Fee.objects.all().count() == 0:
            self.stderr.write(
                "No fees in the database. Did you load fixtures into the " +
                "database first?\n " +
                "(./manage.py loaddata membership/fixtures/membership_fees.json)")
            raise SystemExit()
        self.user = User.objects.get(id=1)
        self.generate(approved=options['approved'],
                      preapproved=options['preapproved'],
                      new=options['new'],
                      duplicates=options['duplicates'],
                      dissociated=options['dissociated'],
                      dissociation_requested=options['dissociation_requested'],
                      deleted=options['deleted'])

    @transaction.atomic
    def generate(self, approved, preapproved, new, duplicates, dissociated, dissociation_requested, deleted):
        if Membership.objects.count() > 0 or Payment.objects.count() > 0:
            self.stderr.write("Database not empty, refusing to generate test data")
            sys.exit(1)
        assert approved + preapproved + new > duplicates
        # Approved members
        initial_index = 0
        index = 1

        for i in range(index, index + approved + dissociated + dissociation_requested + deleted):
            membership = self.create_dummy_member(i)
            if initial_index == 0:
                initial_index = membership.pk
            membership.preapprove(self.user)
            membership.approve(self.user)
            self.create_payment(membership)
        index += approved + dissociated + dissociation_requested + deleted

        # Pre-approved members
        for i in range(index, index + preapproved):
            with transaction.atomic():
                membership = self.create_dummy_member(i)
                membership.preapprove(self.user)
        index += preapproved

        # New applications
        for i in range(index, index + new):
            membership = self.create_dummy_member(i)
        index += new

        # Make a few duplicates for duplicate detection GUI testing
        for i in range(index, index + duplicates):
            if approved > 0 and random() > 0.5:
                # About 50% of duplicates are existing members
                duplicate_source_id = randint(1, approved)
            else:
                # The rest are new applications
                duplicate_source_id = randint(index - 1 - duplicates, index - 1)
            duplicate_of = Membership.objects.get(id=duplicate_source_id)
            membership = self.create_dummy_member(i, duplicate_of=duplicate_of)
        index += duplicates

        management.call_command('makebills')
        for payment in Payment.objects.all():
            try:
                attach_payment_to_cycle(payment)
            except:
                pass

        # Some members disassociate.

        for i in range(initial_index, initial_index + dissociated + dissociation_requested + deleted):
            membership = Membership.objects.get(id=i)
            membership.request_dissociation(self.user)

        for i in range(initial_index, initial_index + dissociated + deleted):
            membership = Membership.objects.get(id=i)
            membership.dissociate(self.user)

        for i in range(initial_index, initial_index + deleted):
            membership = Membership.objects.get(id=i)
            membership.delete_membership(self.user)

    @transaction.atomic
    def create_dummy_member(self, i, duplicate_of=None):
        fname = random_first_name()
        d = {
            'street_address': 'Testikatu %d' % i,
            'postal_code': '%d' % (i + 1000),
            'post_office': 'Paska kaupunni',
            'country': 'Finland',
            'phone': "%09d" % (40123000 + i),
            'sms': "%09d" % (40123000 + i),
            'email': 'user%d@example.com' % i,
            'homepage': 'http://www.example.com/%d' % i,
            'first_name': fname,
            'given_names': '%s %s' % (fname, "Kapsi"),
            'last_name': random_last_name(),
        }

        if duplicate_of is not None:
            d['first_name'] = duplicate_of.person.first_name
            d['last_name'] = duplicate_of.person.last_name

        person = Contact(**d)
        person.save()
        if random() < 0.2:
            public_memberlist = True
        else:
            public_memberlist = False
        membership = Membership(type='P', status='N',
                                person=person,
                                nationality='Finnish',
                                municipality='Paska kaupunni',
                                public_memberlist=public_memberlist,
                                extra_info='Hintsunlaisesti semmoisia tietoja.')

        self.stdout.write(str(person))
        membership.save()

        forward_alias = Alias(owner=membership,
                              name=Alias.email_forwards(membership)[0])
        forward_alias.save()

        login_alias = Alias(owner=membership, account=True,
                            name=choice(Alias.unix_logins(membership)))
        login_alias.save()

        # Services
        forward_alias_service = Service(servicetype=ServiceType.objects.get(servicetype='Email alias'),
                                        alias=forward_alias, owner=membership, data=forward_alias.name)
        forward_alias_service.save()

        unix_account_service = Service(servicetype=ServiceType.objects.get(servicetype='UNIX account'),
                                       alias=login_alias, owner=membership, data=login_alias.name)
        unix_account_service.save()

        if random() < 0.6:
            mysql_service = Service(servicetype=ServiceType.objects.get(servicetype='MySQL database'),
                                    alias=login_alias, owner=membership, data=login_alias.name.replace('-', '_'))
            mysql_service.save()
        if random() < 0.6:
            postgresql_service = Service(servicetype=ServiceType.objects.get(servicetype='PostgreSQL database'),
                                         alias=login_alias, owner=membership, data=login_alias.name)
            postgresql_service.save()
        # End of services

        logger.info("New application %s from %s:." % (str(person), '::1'))
        return membership

    def create_payment(self, membership):
        if random() < 0.3:
            return  # do nothing

        amount = "40.0"
        if random() < 0.2:
            amount = "30.0"

        ref = generate_membership_bill_reference_number(membership.id, datetime.now().year)
        if random() < 0.2:
            ref = str(randint(1000, 1000000))
        payment_count = 1
        if random() < 0.2:
            payment_count = 2
        elif random() < 0.2:
            payment_count = 3
        for i in range(payment_count):
            p = Payment(reference_number=ref,
                        transaction_id=str(uuid4())[:29],
                        payment_day=datetime.now(),
                        amount=Decimal(amount),
                        type="XYZ",
                        payer_name=membership.name())
            p.save()
