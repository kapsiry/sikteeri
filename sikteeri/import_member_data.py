#!/Users/joneskoo/git/sikteeri/env/bin/python
# encoding: utf-8
"""
generate_test_data.py

Created by Joonas Kortesalmi on 2010-06-18.
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

user = User.objects.get(id=1)

# MEMBER_TYPES = (('P', _('Person')),
#                 ('S', _('Supporting')),
#                 ('O', _('Organization')))

def create_member(status, mdata):
    # legacy fields
    # ['application_id', 'sendinfo', 'memberclass', 'applicationtime', 'sms',
    # 'id', 'email', 'website', 'publicwebsite', 'lastname', 'phone',
    # 'firstnames', 'address', 'nationality', 'post', 'removed', 'publicname',
    # 'name', 'mobile', 'residence', 'time', 'publicemail']
    # TODO: latest billing period start date?
    post_index = mdata['post'].find(' ')
    postcode = mdata['post'][:post_index]
    postoffice = mdata['post'][post_index+1:]
    d = {
        'street_address' : mdata['address'],
        'postal_code' : postcode,
        'post_office' : postoffice,
        'country' : mdata['nationality'],
        'phone' : mdata['phone'],
        'sms' : mdata['sms'],
        'email' : mdata['email'],
        'homepage' : mdata['publicwebsite'],
        'first_name' : mdata['name'],
        'given_names' : mdata['firstnames'],
        'last_name' : mdata['lastname'],
        # mdata['application_id'],
        # mdata['sendinfo'],
    }
    
    if not mdata['memberclass']:
        mtype = 'P'
        print "Member type missing for mid %d" % mdata['id']
    elif mdata['memberclass'] == 'member':
        mtype = 'P'
    elif mdata['memberclass'] == 'supporting':
        mtype = 'S'
    person = contact_from_dict(d)
    person.save()
    membership = Membership(id=mdata['id'], type=mtype, status=status,
                            person=person,
                            nationality=mdata['nationality'],
                            municipality=mdata['residence'],
                            extra_info='')
    logging.info("New application %s imported from legacy database." % (str(person)))
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
    # Creating an instance does not touch db and we need and id for the Bill
    billing_cycle.save()
    bill = Bill(cycle=billing_cycle)
    bill.save()
    #bill.send_as_email()
    log_change(membership, user, change_message="Approved")
    

def main():
    import simplejson
    members = simplejson.load(open('jasendata.json'))
    for mid, mdata in members.iteritems():
        assert mid == str(mdata['id'])
        create_member('A', mdata)

if __name__ == '__main__':
    main()
