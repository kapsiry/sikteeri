# Django settings for sikteeri project.

import django.conf.global_settings as DEFAULT_SETTINGS

DEBUG = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Helsinki'
SHORT_DATE_FORMAT = 'd.m.Y'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'fi-fi'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# For development purposes, relative or absolute path to static assets
STATIC_ROOT = 'static/'

# For development purposes
MEMBERSHIP_STATIC_ROOT = '../membership/static/'

# This is the path used in templates for asset URL
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

LOGIN_URL = '/login/'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

TEMPLATE_CONTEXT_PROCESSORS = DEFAULT_SETTINGS.TEMPLATE_CONTEXT_PROCESSORS + (
    "sikteeri.context_processors.is_production",
)

MIDDLEWARE_CLASSES = (
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'sikteeri.ForceDefaultLanguageMiddleware.ForceDefaultLanguageMiddleware',
    'sikteeri.GitVersionHeaderMiddleware.GitVersionHeaderMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'sikteeri.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    "templates/",
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.humanize',
    'django.contrib.comments',
    'membership',
    'services',
    'south',
)

SOUTH_TESTS_MIGRATE = False

# If set, this string will be displayed and sikteeri is disabled
MAINTENANCE_MESSAGE = None

SESSION_COOKIE_SECURE = True
PRODUCTION = True

MESSAGE_STORAGE = 'django.contrib.messages.storage.cookie.CookieStorage'

USE_X_FORWARDED_HOST = True

# Show 30 items per page in listview
ENTRIES_PER_PAGE=30

from local_settings import *

# Sanity checks for settings
from os.path import exists as path_exists

assert(IBAN_ACCOUNT_NUMBER != None)
assert(BIC_CODE != None)
assert(BUSINESS_ID != None)
assert(ORGANIZATIO_REGISTER_NUMBER != None)
assert(BILLING_FROM_EMAIL != None)
assert(BANK_OPERATOR != None)
BILLING_CC_EMAIL
assert(FROM_EMAIL != None)
assert(SYSADMIN_EMAIL != None)
assert(SECRET_KEY != None)
assert(BILL_SUBJECT != None)
assert(ENABLE_REMINDERS != None)
assert(REMINDER_GRACE_DAYS != None)
assert(BILL_DAYS_BEFORE_CYCLE != None)
assert(BILL_DAYS_TO_DUE != None)
assert(TRUSTED_HOSTS != None)
assert(PDF_BILLS != None)
