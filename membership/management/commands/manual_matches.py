# encoding: UTF-8

from __future__ import with_statement

from django.db.models import Q, Sum
from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import NoArgsCommand

import logging
logger = logging.getLogger("sikteeri.membership.management.commands.manual_matches")
from datetime import datetime, timedelta

from membership.models import Bill, BillingCycle, Payment, Membership

import codecs
import csv
import os
import sys

from datetime import datetime
from decimal import Decimal

import logging
logger = logging.getLogger("csvbills")

def process_csv(filename):
    """Actual CSV file processing logic
    """
    num_attached = num_notattached = 0
    sum_attached = sum_notattached = 0
    with open(filename, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            (mid, date, transaction) = row
            try:
                payment = Payment.objects.get(transaction_id=transaction)

                if payment.billingcycle: # Already assigned, do nothing
                    continue
                membership = Membership.objects.get(id=int(mid))
                cycle = membership.billingcycle_set.filter(is_paid=False).latest('start')
                payment.attach_to_cycle(cycle)
                num_attached = num_attached + 1
                sum_attached = sum_attached + payment.amount
                continue
            except Payment.DoesNotExist:
                logger.warning("No transactinon found for id: %s, member :%s" % (transaction, mid))
            except Membership.DoesNotExist:
                logger.warning("Membership %s not found. transaction id: %s" % (mid, transaction))   
                # Payment references a billing cycle for a removed member - ignore
                payment.ignore = True
                payment.save()
            except BillingCycle.DoesNotExist:
                # Payment references a legacy billing cycle - ignore
                payment.ignore = True
                payment.save()
            num_notattached = num_notattached + 1
            sum_notattached = sum_notattached + payment.amount

    logger.info("Processed %s payments total %.2f EUR. Unidentified payments: %s (%.2f EUR)" %
                (num_attached + num_notattached, sum_attached + sum_notattached, num_notattached,
                 sum_notattached))


class Command(BaseCommand):
    args = '<csvfile>'
    help = 'Import manual matches of payments'

    def handle(self, csvfile, **options):
        logger.info("Starting the processing of file %s." %
            os.path.abspath(csvfile))
        try:
            process_csv(csvfile)
        except Exception, e:
            print "Fatal error: %s" % unicode(e)
            logger.error("process_csv failed: %s" % unicode(e))
            sys.exit(1)
        logger.info("Done processing file %s." % os.path.abspath(csvfile))
