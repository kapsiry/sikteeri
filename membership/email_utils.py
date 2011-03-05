# -*- coding: utf-8 -*-

import logging
logger = logging.getLogger("email_utils")

from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.core import mail
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.dispatch import Signal

# Signals
send_as_email = Signal(providing_args=["instance"])
send_preapprove_email = Signal(providing_args=["instance", "user"])

# Signal handlers
def bill_sender(sender, instance=None, **kwargs):
    membership = instance.billingcycle.membership
    if settings.BILLING_CC_EMAIL != None:
        email = EmailMessage(instance.bill_subject(),
                             instance.render_as_text(),
                             settings.BILLING_FROM_EMAIL,
                             [membership.billing_email()],
                             [settings.BILLING_CC_EMAIL],
                             headers={'CC': settings.BILLING_CC_EMAIL})
    else:
        email = EmailMessage(instance.bill_subject(),
                             instance.render_as_text(),
                             settings.BILLING_FROM_EMAIL,
                             [membership.billing_email()])
    connection = mail.get_connection()
    connection.send_messages([email])
    logger.info(u'A bill sent as email to %s: %s' % (membership.billing_email(),
                                                     unicode(instance)))

def preapprove_email_sender(sender, instance=None, user=None, **kwargs):
    from services.models import Service
    from models import MEMBER_TYPES_DICT
    # imported here since on top-level it would lead into a circular import
    email_body = render_to_string('membership/preapprove_mail.txt', {
        'membership': instance,
        'membership_type': MEMBER_TYPES_DICT[instance.type],
        'services': Service.objects.filter(owner=instance),
        'user': user
        })
    sysadmin_email = EmailMessage(_('Kapsi member application %i') % instance.id,
                                  email_body,
                                  settings.FROM_EMAIL,
                                  [settings.SYSADMIN_EMAIL],
                                  headers = {'Reply-To': instance.email_to()})
    connection = mail.get_connection()
    connection.send_messages([sysadmin_email])
    logger.info(u'A preapprove email sent to %s <%s> by %s' % (unicode(instance),
                                                               instance.billing_email(),
                                                               user))
