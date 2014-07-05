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

# Compile translations and run development server
./run-sikteeri.sh

If you want to override settings, create a local settings
file which has "import * from sikteeri.settings" and
export DJANGO_SETTINGS_FILE=production_settings or similar
