REQUIREMENTS
============

* Django 1.6
* Python 2.7
* gettext
* openldap and sasl dev for LDAP support

For production, additionally:
* gunicorn
* PostgreSQL

HOW TO RUN
==========

# Create virtualenv environment
./install-virtualenv.sh

(
If it fails with installing python-ldap on OS X, check that you have the
requirements (SASL, openldap). Hint:
  source env/bin/activate
  pip install -r requirements.txt --global-option=build_ext --global-option="-I$(xcrun --show-sdk-path)/usr/include/sasl"
)

# Activate virtualenv
source env/bin/activate

# Initialize development database
./manage.py migrate && \
./manage.py createsuperuser && \
./manage.py loaddata membership/fixtures/membership_fees.json && \
./manage.py generate_test_data

# Compile translations and run development server
./run-sikteeri.sh

# Access the development server at

    http://127.0.0.1:8000/

# Log in at

    http://127.0.0.1:8000/login/

# Run unit tests (always before committing changes)

./manage.py test

OR with py.test: (requires pip install pytest pytest-cov pytest-django)

./test.sh

If you want to override settings, create a local settings
file which has "import * from sikteeri.settings" and
export DJANGO_SETTINGS_FILE=production_settings or similar

The default settings.py must be the default development
configuration and work out of the box.
