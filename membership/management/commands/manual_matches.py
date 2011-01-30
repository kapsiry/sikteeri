# encoding: UTF-8

from __future__ import with_statement

from django.db.models import Q, Sum
from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import NoArgsCommand
from django.contrib.auth.models import User

import logging
logger = logging.getLogger("manual_matches")
from datetime import datetime, timedelta

from membership.models import Bill, BillingCycle, Payment, Membership
from membership.utils import log_change

import codecs
import csv
import os
import sys

from datetime import datetime
from decimal import Decimal

def process_csv(filename):
    """Actual CSV file processing logic
    """
    num_attached = num_notattached = 0
    sum_attached = sum_notattached = 0
    num_nomember = num_nopayment = num_nocycle = num_old = 0
    log_user = User.objects.get(id=1)
    with open(filename, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            (mid, year, date, reference, transaction) = row
            try:
                membership = Membership.objects.get(id=int(mid))
                cycle = find_cycle(membership, year)
                payment = Payment.objects.get(transaction_id=transaction)

                if payment.billingcycle: # Already assigned, mark cycle as paid
                    if payment.billingcycle != cycle:
                        mark_cycle_paid(cycle, log_user, "One payment for several billing cycles")
                    num_old += 1
                    continue
                payment.attach_to_cycle(cycle)
                log_change(payment, log_user, change_message="Attached by manual_matches")
                num_attached += 1
                sum_attached += payment.amount
                continue
            except Membership.DoesNotExist:
                logger.warning("Membership %s not found. transaction id: %s" % (mid, transaction))
                # Payment references a billing cycle for a removed member - ignore
                ignore_payment(transaction, log_user, "no member")
                num_nomember += 1
            except BillingCycle.DoesNotExist:
                # Payment references a legacy billing cycle - ignore payment
                ignore_payment(transaction, log_user, "legacy payment")
                num_nocycle += 1
            except Payment.DoesNotExist:
                logger.warning("No transaction found for id: %s, member: %s year: %s. Marking as paid anyway" % (transaction, mid, year))
                mark_cycle_paid(cycle, log_user, "Paid by a legacy payment (before 2010)")
                num_nopayment += 1
            num_notattached = num_notattached + 1

    logger.info("Processed %s payments, attached %s payments, total %.2f EUR. Unidentified payments: %s" %
                (num_attached + num_notattached, num_attached, sum_attached, num_notattached))
    logger.info("No members: %s, no cycle: %s, no payment in db: %s, already attached to a cycle: %s" %
                (num_nomember, num_nocycle, num_nopayment, num_old))

def find_cycle(membership, year):
    return membership.billingcycle_set.filter(start__year=year).latest('start')

def ignore_payment(transaction, log_user, reason):
    try:
        payment = Payment.objects.get(transaction_id=transaction)
        if not payment.ignore:
            payment.ignore = True
            payment.save()
            log_change(payment, log_user, change_message="Ignored by manual_matches: %s" % reason)
    except Payment.DoesNotExist:
        pass

def mark_cycle_paid(cycle, log_user, reason):
    if not cycle.is_paid:
        cycle.is_paid = True
        cycle.save()
        log_change(cycle, log_user, change_message=reason)

class Command(BaseCommand):
    args = '<csvfile>'
    help = 'Import manual matches of payments'

    def handle(self, csvfile, **options):
        logger.info("Starting the processing of file %s." %
            os.path.abspath(csvfile))
        process_csv(csvfile)
        try:
            pass
            #process_csv(csvfile)
        except Exception, e:
            print "Fatal error: %s" % unicode(e)
            logger.error("process_csv failed: %s" % unicode(e))
            sys.exit(1)
        logger.info("Done processing file %s." % os.path.abspath(csvfile))
