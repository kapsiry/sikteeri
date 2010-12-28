#!/usr/bin/env python
# encoding: utf-8
"""
import_member_data.py

Created by Joonas Kortesalmi on 2010-06-18.
Copyright (c) 2010 Kapsi Internet-käyttäjät ry. All rights reserved.
"""

import sys
import os
from datetime import datetime, timedelta
from optparse import OptionParser

os.environ['DJANGO_SETTINGS_MODULE'] = 'sikteeri.settings'
sys.path.insert(0, '..')

from django.conf import settings
import logging
from membership.utils import log_change
from django.contrib.auth.models import User
from django.contrib.comments.models import Comment
from membership.models import Contact, Membership, Bill, BillingCycle
from membership.models import Fee, MEMBER_TYPES

user = User.objects.get(id=1)

# MEMBER_TYPES = (('P', _('Person')),
#                 ('S', _('Supporting')),
#                 ('O', _('Organization')))

def create_member(mdata):
    # legacy fields
    # ['application_id', 'sendinfo', 'memberclass', 'applicationtime', 'sms',
    # 'id', 'email', 'website', 'publicwebsite', 'lastname', 'phone',
    # 'firstnames', 'address', 'nationality', 'post', 'removed', 'publicname',
    # 'name', 'mobile', 'residence', 'time', 'publicemail', 'period_start',
    # 'period_end']
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
        'homepage' : mdata['website'],
        'first_name' : mdata['name'],
        'given_names' : mdata['firstnames'],
        'last_name' : mdata['lastname'],
        # mdata['application_id'],
        # mdata['sendinfo'],
    }

    # Hide non-public websites
    if not mdata['publicwebsite']:
        d['homepage'] = ""

    if not mdata['memberclass']:
        mtype = 'P'
        print "Member type missing for member %d" % mdata['id']
    elif mdata['memberclass'] == 'member':
        mtype = 'P'
    elif mdata['memberclass'] == 'supporting':
        mtype = 'S'
    else:
        print "Not importing, member class unknown for member %d" % mdata['id']
        return False
    person = Contact(**d)
    person.save()
    membership = Membership(id=mdata['id'], type=mtype, status='A',
                            created=datetime.utcfromtimestamp(mdata['time']),
                            accepted=datetime.utcfromtimestamp(mdata['time']),
                            person=person,
                            nationality=mdata['nationality'],
                            municipality=mdata['residence'],
                            extra_info='Imported from legacy')
    logging.info("Member %s imported from legacy database." % (unicode(person)))
    membership.save()
    comment = Comment()
    comment.content_object = membership
    comment.user = user
    comment.comment = "Approved"
    comment.site_id = settings.SITE_ID
    comment.submit_date = datetime.utcfromtimestamp(mdata['time'])
    comment.save()
    billing_cycle = BillingCycle(membership=membership,
        start=datetime.strptime(mdata['period_start'], "%Y-%m-%d %H:%M:%S"),
        end=datetime.strptime(mdata['period_end'], "%Y-%m-%d %H:%M:%S")+timedelta(days=1))
    # Creating an instance does not touch db and we need and id for the Bill
    billing_cycle.save()
    bill = Bill(billingcycle=billing_cycle, is_paid=True,
        created=datetime.strptime(mdata['period_start'], "%Y-%m-%d %H:%M:%S"))
    bill.save()
    #bill.send_as_email()
    log_change(membership, user, change_message="Imported from legacy")
    return True
    

def main(filename):
    import simplejson
    members = simplejson.load(open(filename, 'r'))
    for mid, mdata in members.iteritems():
        assert mid == str(mdata['id'])
        create_member(mdata)

if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-f", "--file", dest="filename",
                      help="read member data from FILE", metavar="FILE",
                      default="jasendata.json")
    (options, args) = parser.parse_args()

    if not os.path.isfile(options.filename):
        parser.error("File '%s' not found." % options.filename)
    main(options.filename)
