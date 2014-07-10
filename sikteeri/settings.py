# Django development settings for sikteeri project.
# For production use, override with
#
#   --settings=production_settings
#
# and have production_settings.py
#
#   import * from settings
#

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

import django.conf.global_settings as DEFAULT_SETTINGS

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True
TEMPLATE_DEBUG = True

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'z$g77fzdhwi%lrn-8zezn995*=m!s_nb*k&7=fo(9ppf6(s%_a'

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.6/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []

# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}

# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# http://www.i18nguy.com/unicode/language-identifiers.html
TIME_ZONE = 'Europe/Helsinki'
SHORT_DATE_FORMAT = 'd.m.Y'
LANGUAGE_CODE = 'fi-fi'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = False

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

STATIC_URL = '/static/'

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'sikteeri/static'),
    os.path.join(BASE_DIR, 'membership/static'),
)

TEMPLATE_DIRS = (
    os.path.join(BASE_DIR, 'sikteeri/templates/'),
)

TEMPLATE_CONTEXT_PROCESSORS = DEFAULT_SETTINGS.TEMPLATE_CONTEXT_PROCESSORS + (
    "sikteeri.context_processors.is_production",
)

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.humanize',
    'django.contrib.comments',
    'django.contrib.staticfiles',
    'membership',
    'services',
    'south',
    'debug_toolbar',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'sikteeri.ForceDefaultLanguageMiddleware.ForceDefaultLanguageMiddleware',
    'sikteeri.GitVersionHeaderMiddleware.GitVersionHeaderMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'sikteeri.urls'

WSGI_APPLICATION = 'sikteeri.wsgi.application'

LOGIN_URL = 'login'


# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

SOUTH_TESTS_MIGRATE = False

# If set, this string will be displayed and sikteeri is disabled
MAINTENANCE_MESSAGE = None

MESSAGE_STORAGE = 'django.contrib.messages.storage.cookie.CookieStorage'

# Show 30 items per page in listview
ENTRIES_PER_PAGE=30

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
BILL_DAYS_BEFORE_CYCLE = 14 # days
# New bills will have a due date 2 weeks in the future
BILL_DAYS_TO_DUE = 14 # days
# Send reminders 2 weeks after previous due day
REMINDER_GRACE_DAYS = 14 # days
ENABLE_REMINDERS = False
# Reminders will be additionally sent to account@domain if specified
UNIX_EMAIL_DOMAIN = 'example.com'

# Generic email settings
FROM_EMAIL = 'from.nonbill@example.com'
SYSADMIN_EMAIL = 'admins@example.com'

# Don't really send email messages, only show them on console
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
EMAIL_SUBJECT_PREFIX = '[sikteeri-TEST] '

# Paper reminder templates
PAPER_REMINDER_TEMPLATE = '/dev/null'

LOGIN_REDIRECT_URL = 'frontpage'

# When PRODUCTION is true, show production graphics and colours.
# Otherwise indicate that this is a development environment (logo, colour)
PRODUCTION = False
