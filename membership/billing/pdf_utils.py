"""
Some functions that cannot be in pdf.py file to prevent import loop.
"""

from io import BytesIO
import logging
from tempfile import NamedTemporaryFile

from django.conf import settings
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
        buffer = BytesIO()

        # Select template bill/reminder
        if bill.is_reminder():
            # This is reminder
            p = pdf.PDFReminder(buffer)
        else:
            p = pdf.PDFInvoice(buffer)
        p.addBill(bill, payments=payments)
        p.generate()
        buffer.seek(0)
        myfile = File(buffer)
        bill.pdf_file.save('bill_{id}.pdf'.format(id=bill.id), myfile)
        buffer.close()
    return bill.pdf_file.read()

