#!/usr/bin/env python
# encoding: utf-8
"""
generate_test_data.py

Created by Joonas Kortesalmi on 2010-02-04.
Copyright (c) 2010 Kapsi Internet-käyttäjät ry. All rights reserved.
"""

import sys
import os
from datetime import datetime

os.environ['DJANGO_SETTINGS_MODULE'] = 'sikteeri.settings'
sys.path.insert(0, '..')

from django.conf import settings
import logging
from membership.utils import log_change
from django.contrib.auth.models import User
from django.contrib.comments.models import Comment
from membership.views import contact_from_dict
from membership.models import Membership, Bill, BillingCycle, Fee, MEMBER_TYPES

fees = Fee.objects.all()
if len(fees) == 0:
	print "No fees in the database, generating default fees..."
        for k, v in MEMBER_TYPES:
            print "Creating fee for member type %s..." % k,
            fee = Fee()
            fee.start = datetime.now()
            fee.sum = settings.MEMBERSHIP_FEE
            fee.type = k
            fee.save()
            print "done."

user = User.objects.get(id=1)

def create_dummy_member(i, status):
    d = {
        'street_address' : 'Testikatu %d'%i,
        'postal_code' : '%d' % (i+1000),
        'post_office' : 'Paska kaupunni',
        'country' : 'Finland',
        'phone' : "%09d" % (40123000 + i),
        'sms' : "%09d" % (40123000 + i),
        'email' : 'user%d@example.com' % i,
        'homepage' : 'http://www.example.com/%d'%i,
        'first_name' : 'Testaaja%d'%i,
        'given_names' : 'Veijo Testaaja%d'%i,
        'last_name' : 'Testiperhe',
    }
    person = contact_from_dict(d)
    person.save()
    membership = Membership(type='P', status=status,
                            person=person,
                            nationality='Finnish',
                            municipality='Paska kaupunni',
                            extra_info='Hintsunlaisesti semmoisia tietoja.')
    logging.info("New application %s from %s:." % (str(person), '::1'))
    print unicode(person)
    membership.save()

def membership_preapprove(i):
    membership = Membership.objects.get(id=i)
    membership.status = 'P'
    membership.save()
    comment = Comment()
    comment.content_object = membership
    comment.user = user
    comment.comment = "Preapproved"
    comment.site_id = settings.SITE_ID
    comment.submit_date = datetime.now()
    comment.save()
    log_change(membership, user, change_message="Preapproved")


def approve(i):
    membership = Membership.objects.get(id=i)
    membership.status = 'A'
    comment = Comment()
    comment.content_object = membership
    comment.user = user
    comment.comment = "Approved"
    comment.site_id = settings.SITE_ID
    comment.submit_date = datetime.now()
    comment.save()
    billing_cycle = BillingCycle(membership=membership)
    billing_cycle.save() # Creating an instance does not touch db and we need and id for the Bill
    bill = Bill(cycle=billing_cycle)
    bill.save()
    #bill.send_as_email()
    log_change(membership, user, change_message="Approved")
    

def main():
    # Approved members
    for i in xrange(1,2000):
        create_dummy_member(i, 'N')
        membership_preapprove(i)
        approve(i)
    # Pre-approved members
    for i in xrange(2000,2100):
        create_dummy_member(i, 'N')
        membership_preapprove(i)
    # New applications
    for i in xrange(2100,2200):
        create_dummy_member(i, 'N')

        
    

if __name__ == '__main__':
    main()
