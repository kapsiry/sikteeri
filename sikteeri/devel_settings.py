# -*- coding: utf-8 -*-

# These are dummy values for development use!
# These can be used as good defaults and overridden in local_settings if
# needed but are unsuitable for production.

# NOT SECURE! Must be random and long enough to be secure.
SECRET_KEY = 'secret'

# Secure cookies require https, for local development needs to be False.
# Default = True
SESSION_COOKIE_SECURE = False

DATABASES = {
    'default' : {
        'NAME': 'sikteeri_test.sqlite',
        'ENGINE': 'django.db.backends.sqlite3',
        'USER': '',
        'PASSWORD' : '',
    }
}

# Hosts allowed to fetch statistics etc. without authentication
TRUSTED_HOSTS = ['127.0.0.1', '::1']

# Billing settings
IBAN_ACCOUNT_NUMBER = 'FI00 0000 0000 0000 00'
BIC_CODE = 'AAAAAAAA'
BILLING_FROM_EMAIL = 'from@example.com'
BILLING_CC_EMAIL = None
BILL_SUBJECT = 'Test bill, ignore'
REMINDER_SUBJECT = 'Test reminder, ignore'
# Send bills 2 weeks before new cycle starts
BILL_DAYS_BEFORE_CYCLE = 14
# New bills will have a due date 2 weeks in the future
BILL_DAYS_TO_DUE = 14
# Send reminders 2 weeks after previous due day
REMINDER_GRACE_DAYS = 14
ENABLE_REMINDERS = False
# Reminders will be additionally sent to account@domain if specified
UNIX_EMAIL_DOMAIN = 'example.com'

# Generic email settings
FROM_EMAIL = 'from.nonbill@example.com'
SYSADMIN_EMAIL = 'admins@example.com'

# Don't really send email messages, only show them on console
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_SUBJECT_PREFIX = '[sikteeri-TEST] '

DEBUG = True
TEMPLATE_DEBUG = DEBUG

# When PRODUCTION is true, show final graphics and colours.
# Otherwise indicate that this is a development environment (logo, colour)
PRODUCTION = False
