REQUIREMENTS
============

* Django 1.6
* Python 2.7
* gettext

For production, additionally:
* gunicorn
* PostgreSQL

HOW TO RUN
==========

# Create virtualenv environment
./install-virtualenv.sh

# Activate virtualenv
source ~/env/sikteeri/bin/activate

# Initialize development database
./manage.py syncdb && \
./manage.py migrate && \
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

If you want to override settings, create a local settings
file which has "import * from sikteeri.settings" and
export DJANGO_SETTINGS_FILE=production_settings or similar

The default settings.py must be the default development
configuration and work out of the box.
