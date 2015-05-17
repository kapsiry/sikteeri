#!/usr/bin/env python
# encoding: utf-8

from __future__ import unicode_literals

"""
Copyright (c) 2014-2015 Kapsi Internet-käyttäjät ry. All rights reserved.

Generates bill list in procountor format and emails it to relevant persons.
"""

import argparse
from datetime import datetime
import logging

from django.core.management.base import BaseCommand
from django.core import mail
from django.conf import settings

from membership.billing.procountor_csv import create_csv


logger = logging.getLogger("membership.billing.procountor")


def valid_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(s)
        raise argparse.ArgumentTypeError(msg)


class Command(BaseCommand):
    help = 'Closes the specified poll for voting'

    def add_arguments(self, parser):
        parser.add_argument('-s', "--startdate", help="Start Date (YYYY-MM-DD)",
                            default=None, type=valid_date)
        parser.add_argument('-e', "--email", help="Send CSV by email (default stdout)",
                            default=None)

    def email_body(self):
        return """Hei,

Liitteenä sikteeristä tänään {date} lähteneet laskut Procountoriin vientiä varten.
Mukana myös uudet hyvityslaskut.
""".format(date=self.date_human())

    @staticmethod
    def date_human():
        return datetime.now().strftime('%d.%m.%Y')

    def handle(self, *args, **options):
        start = options['startdate'] or datetime.now()

        # Mark cancelled bills exported only when they are sent by email
        mark_cancelled = bool(options['email'])

        content = create_csv(start=datetime(year=start.year, month=start.month, day=start.day),
                             mark_cancelled=mark_cancelled)

        # Send only if needed
        if content:
            if options['email']:
                email = mail.EmailMessage(
                    subject='Sikteerin Procountor-vienti {date}'.format(date=self.date_human()),
                    body=self.email_body(),
                    from_email=settings.FROM_EMAIL,
                    to=[options['email']],
                    bcc=[])
                email.attach('procountor-vienti-%s.csv' % start.strftime("%Y-%m-%d"), content, 'text/csv')
                email.send()
                message = "Sent Procountor bill list CSV by email"
            else:
                self.stdout.write(content)
                message = 'Wrote Procountor bill list CSV to console'
            logger.info(message)
        else:
            message = "No bills to send"
            logger.info(message)
            self.stdout.write(message)
            self.stdout.write("\n")
