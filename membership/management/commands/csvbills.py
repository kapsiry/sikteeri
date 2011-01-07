# encoding: UTF-8

from __future__ import with_statement

from django.db.models import Q, Sum
from django.core.management.base import LabelCommand
from django.core.exceptions import ObjectDoesNotExist

import codecs
import csv
import os

from datetime import datetime
from decimal import Decimal

import logging
logger = logging.getLogger("csvbills")

from membership.models import Bill, BillingCycle, Payment

class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8

    <http://docs.python.org/library/csv.html#examples>
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")


class UnicodeReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.

    <http://docs.python.org/library/csv.html#examples>
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return [unicode(s, "utf-8") for s in row]

    def __iter__(self):
        return self

class UnicodeDictReader(UnicodeReader):
    """A CSV reader which stores the headers from the first line
    """
    def __init__(self, *args, **kw):
        UnicodeReader.__init__(self, *args, **kw)
        # Read headers from first line
        self.headers = UnicodeReader.next(self)

    def next(self):
        row = UnicodeReader.next(self)
        return dict(zip(self.headers, row))

class RequiredFieldNotFoundException(Exception): pass

class OpDictReader(UnicodeDictReader):
    '''Reader for Osuuspankki CSV file format

    The module converts Osuuspankki CSV format data into a more usable form.'''

    # If these fields are not found on the first line, an exception is raised
    REQUIRED_COLUMNS = ['date', 'amount', 'transaction']

    # Translation table from Osuuspankki CSV format to short names
    OP_CSV_TRANSLATION = {u'Kirjauspäivä'       : 'date',
                          u'Arvopäivä'          : 'value_date',
                          u'Määrä EUROA'        : 'amount',
                          u'Tapahtumalajikoodi' : 'event_type_code',
                          u'Selitys'            : 'event_type_description',
                          u'Saaja/Maksaja'      : 'fromto',
                          u'Saajan tilinumero'  : 'account',
                          u'Viite'              : 'reference',
                          u'Viesti'             : 'message',
                          u'Arkistotunnus'      : 'transaction'}

    def __init__(self, f, delimiter=';', encoding="iso8859-1", *args, **kw):
        UnicodeDictReader.__init__(self, f, delimiter=delimiter,
            encoding=encoding, *args, **kw)
        # Translate headers
        h = self.headers
        for i in xrange(0, len(h)):
            self.headers[i] = self.OP_CSV_TRANSLATION.get(h[i], h[i])
        # Check that all required columns exist in the header
        for name in self.REQUIRED_COLUMNS:
            if name not in self.headers:
                raise RequiredFieldNotFoundException("CSV format is invalid")

    def next(self):
        row = UnicodeDictReader.next(self)
        if len(row) == 0:
            return None
        row['amount'] = Decimal(row['amount'].replace(",", "."))
        row['date'] = datetime.strptime(row['date'], "%d.%m.%Y")
        row['reference'] = row['reference'].replace(' ', '').lstrip('0')
        if row.has_key('value_date'):
            row['value_date'] = datetime.strptime(row['value_date'], "%d.%m.%Y")
        return row

def row_to_payment(row):
    # FIXME: should replace decodes with a decoding CSV 'dialect'
    try:
        p = Payment.objects.get(transaction_id__exact=row['transaction'])
        return p
    except Payment.DoesNotExist:
        p = Payment(payment_day=row['date'],
                    amount=row['amount'],
                    type=row['event_type_description'],
                    payer_name=row['fromto'],
                    reference_number=row['reference'],
                    message=row['message'],
                    transaction_id=row['transaction'])
    return p

def process_csv(filename):
    """Actual CSV file processing logic
    """
    with open(filename, 'r') as f:
        reader = OpDictReader(f)
        for row in reader:
            if row == None:
                continue
            if row['amount'] < 0: # Transaction is paid by us, ignored
                continue
            payment = row_to_payment(row)

            # Do nothing if this payment hasn't been assigned
            if payment.billingcycle:
                continue

            try:
                reference = payment.reference_number
                cycle = BillingCycle.objects.get(reference_number=reference)
                payment.billingcycle = cycle
                payment.save()
                logger.info("Payment %s attached to cycle %s." % (repr(payment),
                    repr(payment.billingcycle)))
                data = payment.billingcycle.payment_set.aggregate(Sum('amount'))
                total_paid = data['amount__sum']
                if total_paid >= cycle.sum:
                    cycle.is_paid = True
                    cycle.save()
                    logger.info("Cycle %s marked as paid, total paid: %.2f." % (
                        repr(cycle), total_paid))
            except BillingCycle.DoesNotExist:
                logger.warning("No billing cycle found for %s" % payment.reference_number)
                continue # Failed to find cycle for this reference number


class Command(LabelCommand):
    help = 'Find expiring billing cycles, send bills, send reminders'

    def handle_label(self, label, **options):
        logger.info("Starting the processing of file %s." % os.path.abspath(label))
        process_csv(label)
        logger.info("Done processing file %s." % os.path.abspath(label))
