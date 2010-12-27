from __future__ import with_statement

import os
from datetime import datetime
from decimal import Decimal, getcontext
import logging
logger = logging.getLogger("sikteeri.membership.management.commands.csvbills")
import csv

from django.core.management.base import LabelCommand

from membership.models import *
from membership.utils import *

def row_to_payment(row):
    try:
        payment = Payment.objects.get(transaction_id__exact=row[8])
        return payment
    except Payment.DoesNotExist, dne:
        pass

    payment = Payment(payment_day=datetime.strptime(row[0], "%d.%m.%Y"),
                      amount=Decimal(row[1].replace(",", ".")),
                      type=row[3],
                      payer_name=unicode(row[4]),
                      reference_number=unicode(row[6]),
                      message=unicode(row[7]),
                      transaction_id=unicode(row[8]))
    return payment

def process_csv(file):
    with open(file, 'r') as f:
        reader = csv.reader(f, delimiter=';', quotechar='\\')
        for row in reader:
            if Decimal(row[1].replace(",", ".")) < 0: # Transaction is from us to someone else
                continue
            payment = row_to_payment(row)

            if payment.bill != None and payment.bill.billingcycle.is_paid():
                continue

            payment.save()
            try:
                payment.bill = Bill.objects.filter(reference_number__exact=row[6]).order_by('-due_date')[0]
                payment.save()
                logger.info("Payment %s attached to bill %s." % (repr(payment), repr(bill)))
            except IndexError, ie:
                logger.warning("No matching bill found for %s." % repr(payment))

            if payment.bill is not None and \
                   payment.amount >= bill.billingcycle.sum:
                bill.is_paid = True
                bill.save()
                logger.info("Marking bill %s as paid (amount %s)." % (repr(bill), str(payment.amount)))
            elif payment.bill is not None:
                logger.warning("Not marking bill %s as paid (amount %s, payment %s)." % (repr(bill), str(payment.amount, repr(payment))))


class Command(LabelCommand):
    help = 'Find expiring billing cycles, send bills, send reminders'

    def handle_label(self, label, **options):
        logger.info("Starting the processing of file %s." % os.path.abspath(label))
        process_csv(label)
        logger.info("Done processing file %s." % os.path.abspath(label))
