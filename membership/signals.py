# -*- coding: utf-8 -*-

from django.dispatch import Signal

import logging
logger = logging.getLogger("membership.signals")


# Signals
send_as_email = Signal()
send_preapprove_email = Signal()
send_duplicate_payment_notice = Signal()
