# -*- coding: utf-8 -*-

from decimal import Decimal

class ReferenceNumberException(Exception): pass
class ReferenceNumberFormatException(ReferenceNumberException): pass
class IBANFormatException(ReferenceNumberException): pass
class InvalidAmountException(ReferenceNumberException): pass
class DueDateFormatException(ReferenceNumberException): pass

def generate_membership_bill_reference_number(membership_id, bill_year):
    # [jäsennumero] yyxxz
    # jossa yy=vuosi kahdella numerolla, xx=maksutapahtumakoodi ja z tarkistenumero
    # 01 on ollut perinteisesti jäsenmaksun maksutapahtumakoodi
    bill_type_suffix = "01"

    return add_checknumber("%i%s%s" % \
                           (membership_id,
                            str(bill_year)[-2:],
                            bill_type_suffix))

def generate_checknumber(number):
    check = 0
    checks = [7, 3, 1]
    for i, digit in enumerate(reversed(number)):
        check += checks[i%3]*int(digit)
    return (10 - check%10)%10

def add_checknumber(number):
    return number + str(generate_checknumber(number))

def check_checknumber(number):
    return number[-1] == str(generate_checknumber(number[:-1]))

def group_right(number, group_size = 5):
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

def canonize_refnum(refnum, digits = 20):
    """Removes any whitespace makes sure the number is 20 digits long"""
    if refnum == None:
        return '0' * digits
    refnum = refnum.replace(' ', '')
    if len(refnum) < digits:
        refnum = refnum.zfill(digits) # zero pad
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
    if duedate == None:
        return '000000'
    else:
        try:
            return duedate.strftime('%y%m%d')
        except AttributeError:
            raise DueDateFormatException("Invalid type for canonize_duedate")
