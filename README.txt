REQUIREMENTS
============

* Django 1.4 (as of 2012/04/14)
* Python 2.6
* gunicorn for production deployment
* gettext

The virtualenv install script installs everything but the Python sqlite
extension.

HOW TO RUN
==========

# Create virtualenv environment
./install-virtualenv.sh

# Create local configuration
cp sikteeri/local_settings.py.template sikteeri/local_settings.py

# Set at least a secret key, preferably a working email address too
$EDITOR sikteeri/local_settings.py

# init virtualenv and set PYTHONPATH=.. (added to activate script in install)
source env/bin/activate

# Compile translations
./run-sikteeri.sh

MIGRATIONS INITIALIZATION
=========================

pip install -r ../requirements.txt                        # install South
PYTHONPATH=.. ./manage.py syncdb                          # South's tables initialized
PYTHONPATH=.. ./manage.py migrate services 0001 --fake    # This needs to be done for each app.
PYTHONPATH=.. ./manage.py migrate membership 0001 --fake

Static assets URLs
==================

* /static/ => sikteeri/static/
* /static/membership/ => membership/static/
* /static/admin/ => Django static root
