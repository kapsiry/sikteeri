#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
generate_test_data.py

Copyright (c) 2010 Kapsi Internet-käyttäjät ry. All rights reserved.
"""

import sys
import os
import logging
logger = logging.getLogger("generate_test_data")

from datetime import datetime

os.environ['DJANGO_SETTINGS_MODULE'] = 'sikteeri.settings'
sys.path.insert(0, '..')

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.comments.models import Comment

from membership.models import Contact, Membership, Bill, BillingCycle, Fee
from membership.test_utils import *

if Fee.objects.all().count() == 0:
    sys.exit("No fees in the database. Did you load fixtures into the " +
	     "database first?\n (./manage.py loaddata test_data.json)")

user = User.objects.get(id=1)

def create_dummy_member(i):
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
    membership = Membership(type='P', status='N',
                            person=person,
                            nationality='Finnish',
                            municipality='Paska kaupunni',
                            extra_info='Hintsunlaisesti semmoisia tietoja.')
    logger.info("New application %s from %s:." % (str(person), '::1'))
    print unicode(person)
    membership.save()
    return membership

def main():
    # Approved members
    for i in xrange(1,2000):
        membership = create_dummy_member(i)
        membership.preapprove(user)
        membership.approve(user)
    # Pre-approved members
    for i in xrange(2000,2100):
        membership = create_dummy_member(i)
        membership.preapprove(user)
    # New applications
    for i in xrange(2100,2200):
        membership = create_dummy_member(i)

if __name__ == '__main__':
    main()
