#!/usr/bin/env python
# encoding: utf-8
"""
import_member_data.py

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
logger = logging.getLogger("import_member_data")

from django.contrib.auth.models import User

from membership.utils import log_change
from membership.models import Contact, Membership, Bill, BillingCycle
from membership.models import Fee, MEMBER_TYPES

from services.models import Alias

user = User.objects.get(id=1)

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
        'phone' : mdata['phone'].replace(" ", "").replace("-", ""),
        'sms' : mdata['sms'].replace(" ", "").replace("-", ""),
        'email' : mdata['email'].strip(" "),
        'homepage' : mdata['website'].strip(" "),
        'first_name' : mdata['name'].strip(" "),
        'given_names' : mdata['firstnames'].strip(" "),
        'last_name' : mdata['lastname'].strip(" "),
        # mdata['application_id'],
        # mdata['sendinfo'],
    }

    # Hide non-public websites
    if not mdata['publicwebsite']:
        d['homepage'] = ""

    if not mdata['memberclass']:
        mtype = 'P'
        print >> sys.stderr, "# Member type missing for member %d" % mdata['id']
    elif mdata['memberclass'] == 'member':
        mtype = 'P'
    elif mdata['memberclass'] == 'supporting':
        mtype = 'S'
    else:
        print >> sys.stderr, "! Not importing, member class unknown for member %d" % mdata['id']
        return False
    person = Contact(**d)
    person.save()
    membership = Membership(id=mdata['id'], type=mtype, status='A',
                            created=datetime.utcfromtimestamp(mdata['time']),
                            approved=datetime.utcfromtimestamp(mdata['time']),
                            person=person,
                            nationality=mdata['nationality'],
                            municipality=mdata['residence'],
                            extra_info='Imported from legacy',
                            public_memberlist=bool(mdata['publicname']))
    logger.info("Member %s imported from legacy database." % (unicode(person)))
    membership.save()

    # Create a period only if there already is one previously. Else let
    # makebills create one.
    if mdata.has_key('period_start'):
        billing_cycle = BillingCycle(membership=membership, is_paid=False,
                                     start=datetime.strptime(mdata['period_start'], "%Y-%m-%d %H:%M:%S"),
                                     end=datetime.strptime(mdata['period_end'], "%Y-%m-%d %H:%M:%S")+timedelta(days=1))
        billing_cycle.save()
        bill = Bill(billingcycle=billing_cycle)
        bill.save()
        # Due to auto_now_add, need to save first before changing
        bill.created=datetime.strptime(mdata['bill_creation'], "%Y-%m-%d %H:%M:%S")
        bill.due_date=datetime.strptime(mdata['bill_dueday'], "%Y-%m-%d %H:%M:%S")
        bill.save()
    for alias in mdata['aliases']:
        a = Alias(owner=membership, name=alias, account=False,
            created=membership.created)
        a.save()
    log_change(membership, user, change_message="Imported into system")
    return True


def main(filename):
    import simplejson
    members = simplejson.load(open(filename, 'r'))
    print >> sys.stderr, "# %i items, starting processing." % len(members)
    processed = 0
    for mid, mdata in members.iteritems():
        assert mid == str(mdata['id'])
        create_member(mdata)
        processed = processed + 1
        if processed % 100 == 0:
            print >> sys.stderr, "# %i items processed" % processed
    print >> sys.stderr, "# %i items in total processed" % processed


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option("-f", "--file", dest="filename",
                      help="read member data from FILE", metavar="FILE")
    (options, args) = parser.parse_args()

    if not options.filename:
        parser.print_help()
        sys.exit(1)
    if not os.path.isfile(options.filename):
        parser.error("File '%s' not found." % options.filename)
    main(options.filename)
