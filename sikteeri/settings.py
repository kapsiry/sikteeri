# Django development settings for sikteeri project.
# For production use, override with
#
#   --settings=production_settings
#
# and have production_settings.py
#
#   import * from settings
#

import django.conf.global_settings as DEFAULT_SETTINGS

DEBUG = True
TEMPLATE_DEBUG = True

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

# brew install postgresql && createdb sikteeri
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'sikteeri',
        'USER': '',
        'PASSWORD': '',
        'HOST': '',
        'PORT': '',
    }
}

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.4/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'Europe/Helsinki'
SHORT_DATE_FORMAT = 'd.m.Y'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'fi-fi'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    'sikteeri/static',
    'membership/static',
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'z$g77fzdhwi%lrn-8zezn995*=m!s_nb*k&7=fo(9ppf6(s%_a'

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
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'sikteeri.ForceDefaultLanguageMiddleware.ForceDefaultLanguageMiddleware',
    'sikteeri.GitVersionHeaderMiddleware.GitVersionHeaderMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'sikteeri.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    "sikteeri/templates/",
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'django.contrib.humanize',
    'django.contrib.comments',
    'django.contrib.staticfiles',
    'membership',
    'services',
    'south',
)

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

#USE_X_FORWARDED_HOST = True

# Show 30 items per page in listview
ENTRIES_PER_PAGE=30

# Secure cookies require https
# SESSION_COOKIE_SECURE = False

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

# When PRODUCTION is true, show final graphics and colours.
# Otherwise indicate that this is a development environment (logo, colour)
PRODUCTION = False
