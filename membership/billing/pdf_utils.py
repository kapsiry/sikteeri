# encoding: utf-8

"""
Some functions that cannot be in pdf.py file to prevent import loop.
"""

from cStringIO import StringIO
import logging

from django.core.files import File
from membership.billing import pdf


logger = logging.getLogger("membership.billing.pdf")


def create_reminder_pdf(cycles, output_file, payments=None):
    """
    Generate reminder pdf with billing cycles `cycles` to file `output_file`
    :param cycles: list of billingcycles
    :param output_file: File-like object
    :return: None
    """
    p = pdf.PDFReminder(output_file)
    try:
        p.addCycles(cycles, payments=payments)
        p.generate()
        return None
    except Exception as e:
        logger.exception(e)
        logger.error("Failed to generate reminder pdf")
        raise


def get_bill_pdf(bill, payments=None):
    """
    Get from pdf_file field or generate pdf for Bill
    :param bill: Bill
    :return: pdf file content
    """

    # Check if PDF cache is valid
    if bill.pdf_file:
        if not bill.pdf_file.storage.exists(bill.pdf_file):
            bill.pdf_file = None

    # If PDF does not exist, generate it
    if not bill.pdf_file:
        pdf_fp = StringIO()

        # Select template bill/reminder
        if bill.is_reminder():
            p = pdf.PDFReminder(pdf_fp)
        else:
            p = pdf.PDFInvoice(pdf_fp)

        p.addBill(bill, payments=payments)
        p.generate()
        pdf_fp.seek(0)
        django_file = File(pdf_fp)
        bill.pdf_file.save("bill_{id}.pdf".format(id=bill.id), django_file)
        pdf_fp.close()

    return bill.pdf_file.read()
