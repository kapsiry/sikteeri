# -*- coding: utf-8 -*-

from django.dispatch import Signal

import logging
logger = logging.getLogger("membership.signals")


# Signals
send_as_email = Signal(providing_args=["instance"])
send_preapprove_email = Signal(providing_args=["instance", "user"])
send_duplicate_payment_notice = Signal(providing_args=["instance","user","billingcycle"])
