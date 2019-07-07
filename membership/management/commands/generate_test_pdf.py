# encoding: utf-8



from decimal import Decimal
import tempfile
from datetime import datetime, timedelta
import uuid

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import translation

from membership.billing import pdf
from membership.models import Contact, Membership, BillingCycle, Payment


@transaction.atomic
def gen_test_PDFs():
    # We are going to revert all database changes to this savepoint
    sid = transaction.savepoint()

    contact = Contact.objects.create(
        first_name="Antero",
        given_names="Antero Ilmari",
        last_name="Marttila",
        street_address="Läppäkuja 16 A 24",
        postal_code="00500",
        post_office="Helsinki",
        country="Suomi",
        phone="40403123123",
        sms="40403123123",
        email="test@example.com")
    member = Membership.objects.create(
        id=4444,
        type='P',
        status='A',
        public_memberlist=True,
        municipality='Helsinki',
        nationality='Suomi',
        birth_year=1990,
        person=contact,
        locked=None)
    cycle = BillingCycle.objects.create(
        membership=member,
        start=datetime.now(),
        end=datetime.now() + timedelta(seconds=31536000),
        sum=Decimal(40.00),
        is_paid=False,
        reference_number="2600013")

    # Generate test invoice PDF
    invoice_file = tempfile.NamedTemporaryFile(
        prefix="sikteeri_invoice", suffix=".pdf", delete=False)
    invoice = pdf.PDFInvoice(invoice_file, cycle)
    invoice.generate()

    # Generate test reminder PDF, with payments smaller than total
    payment = Payment.objects.create(
        billingcycle=cycle,
        reference_number='1234',
        transaction_id=uuid.uuid4(),
        payment_day=datetime.now(),
        amount=30.0,
        payer_name="It was me")
    reminder_file = tempfile.NamedTemporaryFile(
        prefix="sikteeri_reminder", suffix=".pdf", delete=False)
    reminder = pdf.PDFReminder(reminder_file)
    reminder.addCycle(cycle, payments=Payment)
    reminder.generate()

    print("Reminder: %s" % reminder_file.name)
    print("Invoice: %s" % invoice_file.name)
    # Revert database changes
    transaction.savepoint_rollback(sid)


class Command(BaseCommand):
    help = 'Generate test reminder and invoice PDFs'

    def handle(self, *args, **options):
        translation.activate(settings.LANGUAGE_CODE)
        gen_test_PDFs()
