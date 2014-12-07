# encoding: utf-8

from decimal import Decimal
import tempfile
from datetime import datetime, timedelta

from django.conf import settings
from django.core.management.base import NoArgsCommand
from django.utils import translation

from membership.billing import pdf
from membership.models import Contact, Membership, BillingCycle


def gen_test_PDFs():


    contact = Contact()
    contact.first_name = u"Antero"
    contact.given_name = u"Antero Ilmari"
    contact.last_name = u"Marttila"
    contact.street_address = u"Läppäkuja 16 A 24"
    contact.postal_code = u"00500"
    contact.post_office = u"Helsinki"
    contact.country = u"Suomi"
    contact.phone = u"40403123123"
    contact.sms = u"40403123123"
    contact.email = u"test@example.com"


    member = Membership()
    member.id = 4444
    member.type = 'P'
    member.status = 'A'
    member.public_memberlist = True
    member.municipality = 'Helsinki'
    member.nationality = 'Suomi'
    member.birth_year = 1990
    member.person = contact
    member.locked = False

    cycle = BillingCycle()
    cycle.membership = member
    cycle.start = datetime.now()
    cycle.end = datetime.now() + timedelta(seconds=31536000)
    cycle.sum = Decimal(40.00)
    cycle.is_paid = False
    cycle.reference_number = "2600013"


    reminder_file = tempfile.NamedTemporaryFile(prefix="sikteeri_reminder", suffix=".pdf", delete=False)
    invoice_file = tempfile.NamedTemporaryFile(prefix="sikteeri_invoice", suffix=".pdf", delete=False)

    p = pdf.PDFReminder(reminder_file, cycle)
    p.generate()
    pdf.PDFInvoice(invoice_file, cycle).generate()

    print("Reminder: %s" % reminder_file.name)
    print("Invoice: %s" % invoice_file.name)


class Command(NoArgsCommand):
    help = 'Generate test reminder and invoice PDFs'

    def handle_noargs(self, **options):
        translation.activate(settings.LANGUAGE_CODE)
        gen_test_PDFs()
