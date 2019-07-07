# encoding: utf-8


import codecs
import csv

from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _

import logging

from membership.models import BillingCycle, Payment
from membership.utils import log_change

from decimal import Decimal

logger = logging.getLogger(__name__)


class PaymentFromFutureException(Exception): pass


class UTF8Recoder:
    """
    Iterator that reads an encoded stream and reencodes the input to UTF-8

    <http://docs.python.org/library/csv.html#examples>
    """
    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def __next__(self):
        return next(self.reader).encode("utf-8")


class UnicodeReader:
    """
    A CSV reader which will iterate over lines in the CSV file "f",
    which is encoded in the given encoding.

    <http://docs.python.org/library/csv.html#examples>
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        f = UTF8Recoder(f, encoding)
        self.reader = csv.reader(f, dialect=dialect, **kwds)

    def __next__(self):
        row = next(self.reader)
        return row

    def __iter__(self):
        return self


class UnicodeDictReader(UnicodeReader):
    """A CSV reader which stores the headers from the first line
    """
    def __init__(self, *args, **kw):
        UnicodeReader.__init__(self, *args, **kw)
        # Read headers from first line
        self.headers = [x.strip() for x in UnicodeReader.__next__(self)]

    def __next__(self):
        row = UnicodeReader.__next__(self)
        return dict(list(zip(self.headers, row)))


class RequiredFieldNotFoundException(Exception):
    pass


class DuplicateColumnException(Exception):
    pass


class BillDictReader(UnicodeDictReader):
    REQUIRED_COLUMNS = ['date', 'amount', 'transaction']
    CSV_TRANSLATION = {}

    def __init__(self, f, delimiter=';', encoding="iso8859-1", *args, **kw):
        UnicodeDictReader.__init__(self, f, delimiter=delimiter,
            encoding=encoding, *args, **kw)
        # Translate headers
        h = self.headers
        for i in range(0, len(h)):
            self.headers[i] = self._get_translation(h[i])
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


    def _get_translation(self, h):
        """
        Function for custom translations
        """
        return self.CSV_TRANSLATION.get(h, h)

    def _get_row(self, row):
        """
        Function for custom data processing
        """
        return row

    def __next__(self):
        row = self._get_row(UnicodeDictReader.__next__(self))
        if len(row) == 0:
            return None
        row['amount'] = Decimal(row['amount'].replace(",", "."))
        row['date'] = datetime.strptime(row['date'], "%d.%m.%Y")
        row['reference'] = row['reference'].replace(' ', '').lstrip('0')
        row['transaction'] = row['transaction'].replace(' ', '').replace('/', '')
        if 'value_date' in row:
            row['value_date'] = datetime.strptime(row['value_date'], "%d.%m.%Y")
        return row


class OpDictReader(BillDictReader):
    """Reader for Osuuspankki CSV file format

    The module converts Osuuspankki CSV format data into a more usable form."""

    # If these fields are not found on the first line, an exception is raised
    REQUIRED_COLUMNS = ['date', 'amount', 'transaction']

    # Translation table from Osuuspankki CSV format to short names
    OP_CSV_TRANSLATION = {'Kirjauspäivä'       : 'date',
                          'Arvopäivä'          : 'value_date',
                          'Tap.pv'             : 'date', # old format
                          'Määrä EUROA'        : 'amount',
                          'Määrä'              : 'amount',
                          'Tapahtumalajikoodi' : 'event_type_code',
                          'Selitys'            : 'event_type_description',
                          'Saaja/Maksaja'      : 'fromto',
                          'Saajan tilinumero'  : 'account', # old format
                          'Saajan tilinumero ja pankin BIC' : 'account',
                          'Viite'              : 'reference',
                          'Viesti'             : 'message',
                          'Arkistotunnus'      : 'transaction', # old format
                          'Arkistointitunnus'  : 'transaction'}

    def _get_translation(self, h):
        # Quick and dirty, OP changes this field name too often!
        if h.startswith("Määrä"):
            return "amount"
        return self.OP_CSV_TRANSLATION.get(h, h)


class ProcountorDictReader(BillDictReader):

    REQUIRED_COLUMNS = ['date', 'amount', 'transaction']

    CSV_TRANSLATION = {'Kirjauspäivä'       : 'date',
                       'Arvopäivä'          : 'value_date',
                       'Maksupäivä'         : 'date',
                       'Maksu'              : 'amount',
                       'Summa'              : 'amount',
                       'Kirjausselite'      : 'event_type_description',
                       'Maksaja'            : 'fromto',
                       'Nimi'               : 'fromto',
                       'Tilinro'            : 'account',
                       'Viesti'             : 'message',
                       'Viitenumero'        : 'reference',
                       'Arkistointitunnus'  : 'transaction',
                       'Oikea viite'        : 'real_reference',
                     }

    def _get_row(self, row):
        if 'real_reference' in row:
            row['reference'] = row['real_reference']
        return row


def process_op_csv(file_handle, user=None):
    logger.info("Starting OP payment CSV processing...")
    reader = OpDictReader(file_handle)
    return process_payments(reader)


def process_procountor_csv(file_handle, user=None):
    logger.info("Starting procountor payment CSV processing...")
    reader = ProcountorDictReader(file_handle)
    return process_payments(reader)


def attach_payment_to_cycle(payment, user=None):
    """
    Outside of this module, this function is mainly used by
    generate_test_data.py.
    """
    if payment.ignore == True or payment.billingcycle != None:
        raise Exception("Unexpected function call. This shouldn't happen.")
    reference = payment.reference_number
    cycle = BillingCycle.objects.get(reference_number=reference)
    if cycle.is_paid == False or cycle.amount_paid() < cycle.sum:
        payment.attach_to_cycle(cycle, user=user)
    else:
        # Don't attach a payment to a cycle with enough payments
        payment.comment = _('duplicate payment')
        payment.duplicate = True
        log_user = User.objects.get(id=1)
        log_change(payment, log_user, change_message="Payment not attached due to duplicate payment")
        payment.save()
        return None
    return cycle


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
                    message=row['message'][:255],
                    transaction_id=row['transaction'])
    return p


def process_payments(reader, user=None):
    """
    Attach bank account events from reader to payments
    """
    return_messages = []
    num_attached = num_notattached = 0
    sum_attached = sum_notattached = 0
    for row in reader:
        if row is None:
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
            cycle = attach_payment_to_cycle(payment, user=user)
            if cycle:
                msg = _("Attached payment %(payment)s to cycle %(cycle)s") % {
                        'payment': str(payment), 'cycle': str(cycle)}
                logger.info(msg)
                return_messages.append((None, None, msg))
                num_attached = num_attached + 1
                sum_attached = sum_attached + payment.amount
            else:
                # Payment not attached to cycle because enough payments were attached
                msg = _("Billing cycle already paid for %s. Payment not attached.") % payment
                return_messages.append((None, None, msg))
                logger.info(msg)
                num_notattached = num_notattached + 1
                sum_notattached = sum_notattached + payment.amount
        except BillingCycle.DoesNotExist:
            # Failed to find cycle for this reference number
            if not payment.id:
                payment.save() # Only save if object not in database yet
                logger.warning("No billing cycle found for %s" % payment.reference_number)
                return_messages.append((None, payment.id, _("No billing cycle found for %s") % payment))
                num_notattached = num_notattached + 1
                sum_notattached = sum_notattached + payment.amount

    log_message = "Processed %s payments total %.2f EUR. Unidentified payments: %s (%.2f EUR)" % (
        num_attached + num_notattached, sum_attached + sum_notattached, num_notattached,
        sum_notattached)
    logger.info(log_message)
    return_messages.append((None, None, log_message))
    return return_messages
