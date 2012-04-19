#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generate_test_data.py

Copyright (c) 2010 Kapsi Internet-käyttäjät ry. All rights reserved.
"""

import sys
import os
from random import random, randint, choice
from uuid import uuid4
from decimal import Decimal
import logging
from membership.test_utils import random_first_name, random_last_name, random_municipality, random_email, random_street, random_sex
logger = logging.getLogger("generate_test_data")

from datetime import datetime

os.environ['DJANGO_SETTINGS_MODULE'] = 'sikteeri.settings'
sys.path.insert(0, '..')

from django.core import management
from django.db import transaction
from django.contrib.auth.models import User

from membership.models import Contact, Membership, Fee, Payment

from membership.management.commands.csvbills import attach_payment_to_cycle

from membership.reference_numbers import generate_membership_bill_reference_number

from services.models import Alias, Service, ServiceType

if Fee.objects.all().count() == 0:
    sys.exit("No fees in the database. Did you load fixtures into the " +
	     "database first?\n (./manage.py loaddata test_data.json)")

user = User.objects.get(id=1)

@transaction.commit_manually
def create_dummy_member(i):
    sex = random_sex()
    fname = random_first_name(sex)
    lname = random_last_name()
    d = {
        'street_address' : '%s %d'% (random_street(), i),
        'postal_code' : '%d' % randint(i+1000, 9999),
        'post_office' : '%s' % random_municipality(),
        'country' : 'Finland',
        'phone' : "%09d" % (40123000 + i),
        'sms' : "%09d" % (40123000 + i),
        'email' : random_email(fname, lname),
        'homepage' : 'http://www.example.com/%d'%i,
        'first_name' : fname,
        'given_names' : '%s %s' % (fname, random_first_name(sex)),
        'last_name' : lname,
    }
    person = Contact(**d)
    person.save()
    transaction.commit()
    membership = Membership(type='P', status='N',
                            person=person,
                            nationality='Finnish',
                            municipality=random_municipality(),
                            public_memberlist=random() > 0.7,
                            extra_info='Tietoja tässä.')

    print unicode(person)
    membership.save()
    transaction.commit()

    forward_alias = Alias(owner=membership,
                          name=Alias.email_forwards(membership)[0])
    forward_alias.save()


    transaction.commit()
    login_alias = Alias(owner=membership, account=True,
                        name=choice(Alias.unix_logins(membership)))
    login_alias.save()
    transaction.commit()

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
    transaction.commit()
    # End of services

    logger.info("New application %s from %s:." % (str(person), '::1'))
    return membership

@transaction.commit_manually
def create_payment(membership):
    transaction.commit()
    if random() < 0.7:
        amount = "35.0"
        if random() < 0.2:
            amount = "30.0"
            
        ref = generate_membership_bill_reference_number(membership.id, datetime.now().year)
        if random() < 0.2:
            ref = str(randint(1000, 1000000))
        p = Payment(reference_number=ref,
                    transaction_id=str(uuid4())[0:29],
                    payment_day=datetime.now(),
                    amount=Decimal(amount),
                    type="XYZ",
                    payer_name=membership.name())
        p.save()
        transaction.commit()
        return p


@transaction.commit_manually
def main():
    if Membership.objects.count() > 0 or Payment.objects.count() > 0:
        print "Database not empty, refusing to generate test data"
        transaction.commit()
        sys.exit(1)
    # Approved members
    for i in xrange(1,1000):
        membership = create_dummy_member(i)
        membership.preapprove(user)
        membership.approve(user)
        create_payment(membership)
        transaction.commit()

    # Pre-approved members
    for i in xrange(1000,1100):
        membership = create_dummy_member(i)
        membership.preapprove(user)
        transaction.commit()

    # New applications
    for i in xrange(1100,1200):
        membership = create_dummy_member(i)
        transaction.commit()

    management.call_command('makebills')
    transaction.commit()
    for payment in Payment.objects.all():
        try:
            attach_payment_to_cycle(payment)
            transaction.commit()
        except:
            pass

if __name__ == '__main__':
    main()
