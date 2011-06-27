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

# Address helper
def unix_email(membership):
    if settings.UNIX_EMAIL_DOMAIN:
        from services.models import valid_aliases, Alias
        try:
            alias = valid_aliases(membership).filter(account=True).latest('created')
            return "%s <%s@%s>" % (membership.name(), alias, settings.UNIX_EMAIL_DOMAIN)
        except Alias.DoesNotExist:
            pass
    return None

# Signal handlers
def bill_sender(sender, instance=None, **kwargs):
    membership = instance.billingcycle.membership
    to = [membership.billing_email()]
    if instance.is_reminder():
        if membership.billing_contact:
            to.append(membership.email_to())
        local_email = unix_email(membership)
        if local_email:
            to.append(local_email)
    if settings.BILLING_CC_EMAIL != None:
        email = EmailMessage(instance.bill_subject(),
                             instance.render_as_text(),
                             settings.BILLING_FROM_EMAIL,
                             to,
                             [settings.BILLING_CC_EMAIL],
                             headers={'CC': settings.BILLING_CC_EMAIL})
    else:
        email = EmailMessage(instance.bill_subject(),
                             instance.render_as_text(),
                             settings.BILLING_FROM_EMAIL,
                             to)
    connection = mail.get_connection()
    connection.send_messages([email])
    logger.info(u'A bill sent as email to %s: %s' % (",".join(to),
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
    logger.info(u'A preapprove email sent to %s (%s) by %s' % (unicode(instance),
                                                               instance.billing_email(),
                                                               user))
