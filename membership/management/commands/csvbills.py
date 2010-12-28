from __future__ import with_statement

import os
from datetime import datetime
from decimal import Decimal, getcontext
import logging
logger = logging.getLogger("sikteeri.membership.management.commands.csvbills")
import csv

from django.db.models import Q, F, Sum
from django.core.management.base import LabelCommand

from membership.models import *
from membership.utils import *

def row_to_payment(row):
    # FIXME: should replace decodes with a decoding CSV 'dialect'
    transaction_id = row['arkistointitunnus'].decode("ISO8859-1")
    try:
        p = Payment.objects.get(transaction_id__exact=transaction_id)
        return p
    except Payment.DoesNotExist, dne:
        p = Payment(payment_day=datetime.strptime(row['pvm'], "%Y%m%d"),
                    amount=Decimal(row['summa'].replace(",", ".")),
                    type=row['tapahtuma'].decode("ISO8859-1"),
                    payer_name=row['nimi'].decode("ISO8859-1"),
                    reference_number=row['viite'].decode("ISO8859-1"),
                    message=row['viesti'].decode("ISO8859-1"),
                    transaction_id=transaction_id)
    return p

def process_csv(file):
    with open(file, 'r') as f:
        reader = csv.DictReader(f, delimiter=',')
        for row in reader:
            amount = Decimal(row['summa'].replace(",", "."))
            if amount < 0: # Transaction is paid by us, ignored
                continue
            payment = row_to_payment(row)

            # Do nothing if this payment hasn't been assigned
            if payment.bill:
                print "Bill was already assigned to payment"
                continue

            try:
                q = Q(reference_number=payment.reference_number)
                bill = Bill.objects.filter(q).order_by("-due_date")[0]
                bill.save()
            except IndexError:
                continue # Failed to find bill for this reference number
            payment.bill = bill
            payment.save()
            logger.info("Payment %s attached to bill %s." % (
                repr(payment), repr(bill)))

    # For each unpaid billing cycle, check if paid now
    # FIXME: might not fill specifications. Does it work? :)
    # Needs work and testing.
    cycles = BillingCycle.objects.all().annotate(payments_sum=Sum('bill__payment__amount'))
    paid_cycles = cycles.filter(payments_sum__gte=F('sum'))
    Bill.objects.filter(billingcycle__in=paid_cycles).update(is_paid=True)

class Command(LabelCommand):
    help = 'Find expiring billing cycles, send bills, send reminders'

    def handle_label(self, label, **options):
        logger.info("Starting the processing of file %s." % os.path.abspath(label))
        process_csv(label)
        logger.info("Done processing file %s." % os.path.abspath(label))
