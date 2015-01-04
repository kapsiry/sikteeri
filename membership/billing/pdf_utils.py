# encoding: utf-8

"""
Some functions that cannot be in pdf.py file to prevent import loop.
"""

from cStringIO import StringIO
import logging
from tempfile import NamedTemporaryFile

from django.conf import settings
from django.core.files import File
from membership.billing import pdf
from membership.models import BillingCycle


logger = logging.getLogger("membership.billing.pdf")


def create_reminder_pdf(cycles, output_file):
    """
    Generate reminder pdf with billing cycles `cycles` to file `output_file`
    :param cycles: list of billingcycles
    :param output_file: File-like object
    :return: None
    """
    p = pdf.PDFReminder(output_file)
    try:
        p.addCycles(cycles)
        p.generate()
        return None
    except Exception as e:
        logger.exception(e)
        logger.error("Failed to generate reminder pdf")
        raise


def get_bill_pdf(bill):
    """
    Get from pdf_file field or generate pdf for Bill
    :param bill: Bill
    :return: pdf file content
    """
    if not bill.pdf_file:
        buffer = StringIO()
        if bill.is_reminder():
            # This is reminder
            p = pdf.PDFReminder(buffer)
        else:
            p = pdf.PDFInvoice(buffer)
        p.addBill(bill)
        p.generate()
        buffer.seek(0)
        myfile = File(buffer)
        bill.pdf_file.save('bill_%d.pdf' % bill.id, myfile)
        buffer.close()
    return bill.pdf_file.read()


def generate_pdf_reminders(memberid=None):
    """
    Generate pdf reminders to file.
    :param memberid: optional member id
    :return: path to pdf file
    """
    with NamedTemporaryFile(suffix=".pdf", prefix='sikteeri', delete=False) as target_file:

        cycles = BillingCycle.create_paper_remainder_list(memberid)
        create_reminder_pdf(cycles, target_file)
        return target_file.name

def get_pdf_reminders(memberid=None):
    """
    Generate pdf reminders and return pdf content as string.
    :param memberid: optional member id
    :return: pdf content as string
    """
    buffer = StringIO()
    cycles = BillingCycle.create_paper_remainder_list(memberid)
    if len(cycles) == 0:
        return None
    create_reminder_pdf(cycles, buffer)
    pdf_content = buffer.getvalue()
    buffer.close()
    return pdf_content