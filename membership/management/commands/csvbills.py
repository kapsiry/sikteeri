# encoding: UTF-8

from __future__ import with_statement

from django.db.models import Q, Sum
from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext as _
from django.contrib.auth.models import User

import codecs
import csv
import os

from datetime import datetime, timedelta
from decimal import Decimal

import logging
logger = logging.getLogger("membership.csvbills")

from membership.models import Bill, BillingCycle, Payment
from membership.utils import log_change

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
class DuplicateColumnException(Exception): pass
class PaymentFromFutureException(Exception): pass

class OpDictReader(UnicodeDictReader):
    '''Reader for Osuuspankki CSV file format

    The module converts Osuuspankki CSV format data into a more usable form.'''

    # If these fields are not found on the first line, an exception is raised
    REQUIRED_COLUMNS = ['date', 'amount', 'transaction']

    # Translation table from Osuuspankki CSV format to short names
    OP_CSV_TRANSLATION = {u'Kirjauspäivä'       : 'date',
                          u'Arvopäivä'          : 'value_date',
                          u'Tap.pv'             : 'date', # old format
                          u'Määrä EUROA'        : 'amount',
                          u'Määrä EUROA'        : 'amount',
                          u'Tapahtumalajikoodi' : 'event_type_code',
                          u'Selitys'            : 'event_type_description',
                          u'Saaja/Maksaja'      : 'fromto',
                          u'Saajan tilinumero'  : 'account', # old format
                          u'Saajan tilinumero ja pankin BIC' : 'account',
                          u'Viite'              : 'reference',
                          u'Viesti'             : 'message',
                          u'Arkistotunnus'      : 'transaction', # old format
                          u'Arkistointitunnus'  : 'transaction'}

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
                error = "CSV format is invalid: missing field '%s'." % name
                raise RequiredFieldNotFoundException(error)
        # Check that each field is unique
        for name in self.headers:
            if self.headers.count(name) != 1:
                error = "The field '%s' occurs multiple times in the header"
                raise DuplicateColumnException(error)

    def next(self):
        row = UnicodeDictReader.next(self)
        if len(row) == 0:
            return None
        row['amount'] = Decimal(row['amount'].replace(",", "."))
        row['date'] = datetime.strptime(row['date'], "%d.%m.%Y")
        row['reference'] = row['reference'].replace(' ', '').lstrip('0')
        row['transaction'] = row['transaction'].replace(' ', '').replace('/', '')
        if row.has_key('value_date'):
            row['value_date'] = datetime.strptime(row['value_date'], "%d.%m.%Y")
        return row

def row_to_payment(row):
    try:
        p = Payment.objects.get(transaction_id__exact=row['transaction'])
        return p
    except Payment.DoesNotExist:
        p = Payment(payment_day=min(datetime.now(), row['date']),
                    amount=row['amount'],
                    type=row['event_type_description'],
                    payer_name=row['fromto'],
                    reference_number=row['reference'],
                    message=row['message'],
                    transaction_id=row['transaction'])
    return p

def attach_payment_to_cycle(payment):
    """
    Outside of this module, this function is mainly used by
    generate_test_data.py.
    """
    if payment.ignore == True or payment.billingcycle != None:
        raise Exception("Unexpected function call. This shouldn't happen.")
    reference = payment.reference_number
    cycle = BillingCycle.objects.get(reference_number=reference)
    if cycle.is_paid == False or cycle.amount_paid() < cycle.sum:
        payment.attach_to_cycle(cycle)
    else:
        # Don't attach a payment to a cycle with enough payments
        payment.comment = _('duplicate payment')
        log_user = User.objects.get(id=1)
        log_change(payment, log_user, change_message="Payment not attached due to duplicate payment")
        payment.save()
        return None
    return cycle

def process_csv(file_handle):
    """Actual CSV file processing logic
    """
    return_messages = []
    num_attached = num_notattached = 0
    sum_attached = sum_notattached = 0
    reader = OpDictReader(file_handle)
    for row in reader:
        if row == None:
            continue
        if row['amount'] < 0: # Transaction is paid by us, ignored
            continue
        # Payment in future more than 1 day is a fatal error
        if row['date'] > datetime.now() + timedelta(days=1):
            raise PaymentFromFutureException("Payment date in future")
        payment = row_to_payment(row)

        # Do nothing if this payment has already been assigned or ignored
        if payment.billingcycle or payment.ignore:
            continue

        try:
            cycle = attach_payment_to_cycle(payment)
            if cycle:
                return_messages.append(_("Attached payment {payment} to cycle {cycle}").
                    replace("{payment}", unicode(payment)).replace("{cycle}", unicode(cycle)))
                num_attached = num_attached + 1
                sum_attached = sum_attached + payment.amount
            else:
                # Payment not attached to cycle because enough payments were attached
                return_messages.append(_("Billing cycle already paid for %s. Payment not attached.") % payment)
                num_notattached = num_notattached + 1
                sum_notattached = sum_notattached + payment.amount
        except BillingCycle.DoesNotExist:
            # Failed to find cycle for this reference number
            if not payment.id:
                payment.save() # Only save if object not in database yet
                logger.warning("No billing cycle found for %s" % payment.reference_number)
                return_messages.append(_("No billing cycle found for %s") % payment)
                num_notattached = num_notattached + 1
                sum_notattached = sum_notattached + payment.amount

    log_message ="Processed %s payments total %.2f EUR. Unidentified payments: %s (%.2f EUR)" % \
                  (num_attached + num_notattached, sum_attached + sum_notattached, num_notattached, \
                   sum_notattached)
    logger.info(log_message)
    return_messages.append(log_message)
    return return_messages


class Command(BaseCommand):
    args = '<csvfile> [<csvfile> ...]'
    help = 'Read a CSV list of payment transactions'

    def handle(self, *args, **options):
        for csvfile in args:
            logger.info("Starting the processing of file %s." %
                os.path.abspath(csvfile))
            # Exceptions of process_csv are fatal in command line run
            with open(csvfile, 'r') as file_handle:
                process_csv(file_handle)
            logger.info("Done processing file %s." % os.path.abspath(csvfile))
