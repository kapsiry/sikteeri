# -*- coding: utf-8 -*-

from decimal import Decimal


class ReferenceNumberException(Exception):
    pass


class ReferenceNumberFormatException(ReferenceNumberException):
    pass


class IBANFormatException(ReferenceNumberException):
    pass


class InvalidAmountException(ReferenceNumberException):
    pass


class DueDateFormatException(ReferenceNumberException):
    pass


def generate_membership_bill_reference_number(membership_id, bill_year):
    # [jäsennumero] yyxxz
    # jossa yy=vuosi kahdella numerolla, xx=maksutapahtumakoodi ja z tarkistenumero
    # 01 on ollut perinteisesti jäsenmaksun maksutapahtumakoodi
    bill_type_suffix = "01"

    return add_checknumber("%i%s%s" %
                           (membership_id,
                            str(bill_year)[-2:],
                            bill_type_suffix))


def generate_checknumber(number):
    check = 0
    checks = [7, 3, 1]
    for i, digit in enumerate(reversed(number)):
        check += checks[i % 3] * int(digit)
    return (10 - check % 10) % 10


def add_checknumber(number):
    return number + str(generate_checknumber(number))


def check_checknumber(number):
    return number[-1] == str(generate_checknumber(number[:-1]))


def normalize_reference(text):
    """
    Return the national form of a payment reference found in free text,
    or None if the text is not a valid reference.

    Accepts a national reference ("1234 26011") and an international RF
    reference ("RF25123426011"). Whitespace and leading zeros are
    removed. A reference is accepted only if its check digits are valid.
    """
    if not text:
        return None
    reference = "".join(text.split()).upper()
    if reference.startswith("RF"):
        body = reference[4:]
        if not reference[2:4].isdigit() or not body.isdigit():
            return None
        # ISO 11649: move "RFnn" to the end with R=27, F=15; valid if mod 97 == 1
        if int(body + "2715" + reference[2:4]) % 97 != 1:
            return None
        reference = body
    if not reference.isdigit():
        return None
    reference = reference.lstrip("0")
    # The shortest national reference is three digits and a check digit
    if len(reference) < 4 or len(reference) > 20:
        return None
    if not check_checknumber(reference):
        return None
    return reference


def membership_id_from_reference(reference):
    """
    Return the membership id encoded in a membership fee reference number,
    or None if the reference is not in the membership fee format.

    The format is the one generate_membership_bill_reference_number()
    produces: member id, two-digit year, "01" and a check digit.
    """
    reference = normalize_reference(reference)
    if reference is None or len(reference) < 6:
        return None
    if reference[-3:-1] != "01":
        return None
    return int(reference[:-5])


def group_right(number, group_size=5):
    number = number.replace(" ", "")
    groups = []
    while number:
        groups.insert(0, number[-group_size:])
        number = number[:-group_size]
    return " ".join(groups)


def barcode_4(iban, refnum, duedate, euros, cents=0):
    """
    Return a virtual barcode string with IBAN bank account number
    and a national format reference number according to the barcode
    version 4 specification. Barcode length is always 54 numbers
    http://www.fkl.fi/www/page/fk_www_1293
    """
    ver = "4"
    iban = canonize_iban(iban)
    refnum = canonize_refnum(refnum)
    amount = canonize_sum(euros, cents)
    duedate = canonize_duedate(duedate)
    reserved = "000"
    code = "".join((ver, iban, amount, reserved, refnum, duedate))
    return code


def canonize_iban(iban):
    """Removes any leading letters and makes sure the number is 16 digits long"""
    iban = iban.replace(' ', '')
    if iban.startswith('FI'):
        iban = iban[2:]
    if iban.isdigit() and len(iban) == 16:
        return iban
    raise IBANFormatException("IBAN format is invalid")


def canonize_refnum(refnum, digits=20):
    """Removes any whitespace makes sure the number is 20 digits long"""
    if refnum is None:
        return '0' * digits
    refnum = refnum.replace(' ', '')
    if len(refnum) < digits:
        refnum = refnum.zfill(digits)  # zero pad
    if refnum.isdigit() and len(refnum) == digits and check_checknumber(refnum):
        return refnum
    else:
        raise ReferenceNumberFormatException("Reference number '%s' invalid" %
                                             refnum)


def canonize_sum(euros, cents=0):
    if cents == 0:
        d = Decimal(euros)
        euros = int(d)
        cents = int(d * 100) % 100
    else:
        euros = int(euros)
        cents = int(cents)
    if euros > 999999:
        # Amount too big, return 0
        return '000000' + '00'
    if cents > 99 or euros < 0 or cents < 0:
        raise InvalidAmountException("Amount %s euros %s cents invalid" % (
            euros, cents))
    return '%06u%02u' % (euros, cents)


def canonize_duedate(duedate):
    if duedate is None:
        return '000000'
    else:
        try:
            return duedate.strftime('%y%m%d')
        except AttributeError:
            raise DueDateFormatException("Invalid type for canonize_duedate")
