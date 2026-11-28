# encoding: utf-8

import csv

from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

import logging

from django.conf import settings

from membership.models import BillingCycle, Membership, Payment, STATUS_APPROVED
from membership.reference_numbers import membership_id_from_reference
from membership.utils import log_change

from decimal import Decimal

logger = logging.getLogger(__name__)


class PaymentFromFutureException(Exception):
    pass


class RequiredFieldNotFoundException(Exception):
    pass


class DuplicateColumnException(Exception):
    pass


class BillDictReader(csv.DictReader):
    REQUIRED_COLUMNS = ['date', 'amount', 'transaction']
    CSV_TRANSLATION = {}

    def __init__(self, f, delimiter=';', *args, **kw):
        csv.DictReader.__init__(self, f, delimiter=delimiter, *args, **kw)
        # Translate headers
        h = self.fieldnames
        for i in range(0, len(h)):
            self.fieldnames[i] = self._get_translation(h[i])
        # Check that all required columns exist in the header
        for name in self.REQUIRED_COLUMNS:
            if name not in self.fieldnames:
                error = "CSV format is invalid: missing field '%s'." % name
                raise RequiredFieldNotFoundException(error)
        # Check that each field is unique
        for name in self.fieldnames:
            if self.fieldnames.count(name) != 1:
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
        row = self._get_row(csv.DictReader.__next__(self))
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


# How a payment was matched to a billing cycle
MATCH_REFERENCE = 'reference'
MATCH_OLD_REFERENCE = 'old reference'
MATCH_EARLY_PAYMENT = 'early payment'
MATCH_DESCRIPTIONS = {
    MATCH_OLD_REFERENCE: _('old reference'),
    MATCH_EARLY_PAYMENT: _('early payment'),
}

# Comment set on payments that are left unattached as duplicates
DUPLICATE_COMMENT = _('duplicate payment')
# Comment set on payments that are set aside to wait for the member's next
# bill. The comment is what marks the payment: if an administrator changes
# it, the payment is no longer attached automatically.
EARLY_PAYMENT_COMMENT = _('possible early payment')
AUTOMATIC_COMMENTS_IN_ENGLISH = {
    DUPLICATE_COMMENT: 'duplicate payment',
    EARLY_PAYMENT_COMMENT: 'possible early payment',
}


def _has_comment(payment, comment):
    """
    Tell if the payment has the given automatic comment. The comment was
    saved in the language that was active at the time, so compare with
    both the English and the translated text.
    """
    return payment.comment in (AUTOMATIC_COMMENTS_IN_ENGLISH[comment], str(comment))


def _log_user():
    return User.objects.get(id=1)


def _cycle_accepts_payments(cycle):
    return cycle.is_paid is False or cycle.amount_paid() < cycle.sum


def membership_for_reference(reference):
    """
    Find the membership a reference number belongs to, also when the
    reference is from an earlier billing cycle or from a cycle that is not
    in the database.

    :return: (membership or None, billing cycle with that reference or None)
    """
    try:
        cycle = BillingCycle.objects.get(reference_number=reference)
        return cycle.membership, cycle
    except (BillingCycle.DoesNotExist, BillingCycle.MultipleObjectsReturned):
        pass
    membership_id = membership_id_from_reference(reference)
    if membership_id is None:
        return None, None
    return Membership.objects.filter(id=membership_id).first(), None


def unpaid_cycle_for_old_reference(membership, payment):
    """
    Members keep paying with the reference number of an earlier year, for
    example from a standing order. Find the billing cycle such a payment
    is meant for: the member's oldest unpaid cycle, if the payment covers
    exactly what is still owed on it.

    A payment made long before the cycle was billed is not accepted, so
    that an old unidentified payment is never moved to a new bill.
    """
    if membership is None or membership.status != STATUS_APPROVED:
        return None
    earliest = timedelta(days=settings.EARLY_PAYMENT_MAX_DAYS)
    for cycle in membership.billingcycle_set.filter(is_paid=False).order_by('start'):
        first_bill = cycle.first_bill()
        if first_bill is None or cycle.is_cancelled():
            continue
        if payment.payment_day < first_bill.created - earliest:
            continue
        if cycle.sum - cycle.amount_paid() == Decimal(str(payment.amount)):
            return cycle
    return None


def find_cycle_for_payment(payment, membership, reference_cycle):
    """
    Decide which billing cycle a payment belongs to.

    :param membership: the membership the payment's reference belongs to
    :param reference_cycle: the billing cycle that has the payment's reference
    :return: (cycle, match) where match tells how the cycle was found, or
             (None, None) if there is no cycle that the payment could pay
    """
    if reference_cycle is not None and _cycle_accepts_payments(reference_cycle):
        return reference_cycle, MATCH_REFERENCE
    old_reference_cycle = unpaid_cycle_for_old_reference(membership, payment)
    if old_reference_cycle is not None:
        return old_reference_cycle, MATCH_OLD_REFERENCE
    return None, None


def is_early_payment(membership, payment):
    """
    Tell if a payment was made for a bill that does not exist yet. This
    happens with standing orders: the money arrives with an earlier year's
    reference shortly before the next bill is created.

    The member must have paid everything billed so far, the payment must be
    for the same sum as the latest bill, the next bill must be due to be
    created soon, and the payment must not be from the same day as the
    member's previous payment, which would be a payment made twice by mistake.
    """
    if membership is None or membership.status != STATUS_APPROVED:
        return False
    latest_cycle = membership.billingcycle_set.order_by('end').last()
    if latest_cycle is None or not latest_cycle.is_paid or latest_cycle.sum <= 0:
        return False
    if latest_cycle.sum != Decimal(str(payment.amount)):
        return False
    # makebills creates the next bill during the month in which the cycle ends
    next_bill_from = datetime(latest_cycle.end.year, latest_cycle.end.month, 1)
    if payment.payment_day + timedelta(days=settings.EARLY_PAYMENT_MAX_DAYS) < next_bill_from:
        return False
    previous = Payment.objects.filter(billingcycle__membership=membership).order_by('payment_day').last()
    if previous is not None and payment.payment_day.date() <= previous.payment_day.date():
        return False
    return True


def set_aside_early_payment(payment):
    """
    Mark a payment as handled so that it waits for the member's next bill.
    """
    payment.ignore = True
    payment.comment = EARLY_PAYMENT_COMMENT
    payment.save()
    log_change(payment, _log_user(),
               change_message="Set aside as a possible early payment for the next bill")


def attach_matched_payment(payment, cycle, match, user=None):
    """
    Attach a payment to the cycle found for it and record how it was matched.
    """
    if _has_comment(payment, DUPLICATE_COMMENT) or _has_comment(payment, EARLY_PAYMENT_COMMENT):
        payment.comment = ''
    payment.duplicate = False
    payment.attach_to_cycle(cycle, user=user)
    payment.match = match
    if match != MATCH_REFERENCE:
        log_change(payment, user or _log_user(),
                   change_message="Attached to billing cycle %s by %s (reference %s)" % (
                       cycle, match, payment.reference_number))


def attach_payment_to_cycle(payment, user=None):
    """
    Outside of this module, this function is mainly used by
    generate_test_data.py.

    :return: the billing cycle the payment was attached to, or None if the
             payment was left unattached as a duplicate or an early payment
    :raises BillingCycle.DoesNotExist: if the reference number does not
             lead to any billing cycle
    """
    if payment.ignore is True or payment.billingcycle is not None:
        raise Exception("Unexpected function call. This shouldn't happen.")
    membership, reference_cycle = membership_for_reference(payment.reference_number)
    cycle, match = find_cycle_for_payment(payment, membership, reference_cycle)
    if cycle is not None:
        attach_matched_payment(payment, cycle, match, user=user)
        return cycle
    if is_early_payment(membership, payment):
        set_aside_early_payment(payment)
        return None
    if reference_cycle is None:
        raise BillingCycle.DoesNotExist("No billing cycle for reference %s" % payment.reference_number)
    # Don't attach a payment to a cycle with enough payments
    payment.comment = DUPLICATE_COMMENT
    payment.duplicate = True
    log_change(payment, _log_user(), change_message="Payment not attached due to duplicate payment")
    payment.save()
    return None


def attach_early_payments(cycle):
    """
    Attach the payments that were set aside to wait for this billing cycle.

    :return: list of attached payments
    """
    attached = []
    if cycle.sum <= 0:
        return attached
    set_aside = Payment.objects.filter(billingcycle=None, ignore=True).exclude(reference_number='')
    for payment in set_aside.order_by('payment_day'):
        if cycle.is_paid:
            break
        if not _has_comment(payment, EARLY_PAYMENT_COMMENT):
            continue
        if membership_for_reference(payment.reference_number)[0] != cycle.membership:
            continue
        attach_matched_payment(payment, cycle, MATCH_EARLY_PAYMENT)
        attached.append(payment)
    return attached


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
        if row['amount'] < 0:  # Transaction is paid by us, ignored
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
                if payment.match == MATCH_REFERENCE:
                    msg = _("Attached payment %(payment)s to cycle %(cycle)s") % {
                        'payment': str(payment), 'cycle': str(cycle)}
                else:
                    msg = _("Attached payment %(payment)s to cycle %(cycle)s of member %(member)s by %(match)s") % {
                        'payment': str(payment), 'cycle': str(cycle),
                        'member': cycle.membership.id, 'match': MATCH_DESCRIPTIONS[payment.match]}
                logger.info(msg)
                return_messages.append((None, None, msg))
                num_attached = num_attached + 1
                sum_attached = sum_attached + payment.amount
            elif payment.ignore:
                msg = _("Payment %s set aside as a possible early payment for the next bill.") % payment
                return_messages.append((None, None, msg))
                logger.info(msg)
                num_notattached = num_notattached + 1
                sum_notattached = sum_notattached + payment.amount
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
                payment.save()  # Only save if object not in database yet
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
