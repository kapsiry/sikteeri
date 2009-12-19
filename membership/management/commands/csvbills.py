import csv

from django.core.management.base import LabelCommand

from membership.models import *
from membership.utils import *


class Command(LabelCommand):
    help = 'Find expiring cycles, send bills, send reminders'

    def handle_label(self, label, *options):
        reader = csv.reader(open(label), delimiter=';', quotechar='\\')
        for row in reader:
            if int(row[1]) < 0: # Transaction is from us to someone else
                continue
            payment = Payment(payment_day=row[0], amount=row[1], type=row[3],
                              payer_name=row[4], reference_number=row[6], message=row[7], transaction_id=row[8])
            try:
                payment.bill = Bill.objects.filter(reference_number__exact=row[6]).order('-id')[0]
                if payment.amount >= bill.cycle.sum:
                    bill.is_paid = True
                    bill.save
            except:
                pass
            payment.save()
