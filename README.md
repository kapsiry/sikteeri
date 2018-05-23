<a href="https://codecov.io/github/kapsiry/sikteeri?branch=master">
  <img src="https://codecov.io/github/kapsiry/sikteeri/coverage.svg?branch=master" alt="Coverage via Codecov" />
</a>
<a href="https://travis-ci.org/kapsiry/sikteeri">
  <img src="https://travis-ci.org/kapsiry/sikteeri.svg?branch=master" alt="Test results at Travis CI" />
</a>

REQUIREMENTS
============

The following software is required to install Sikteeri.

* Python 2.7
* gettext
* openldap and sasl dev for LDAP support

For production, additionally:
* PostgreSQL

# HOW TO RUN

## Create virtualenv environment
./install-virtualenv.sh

OR you may create and activate virtualenv from requirements.txt manually.

## Activate virtualenv
source env/bin/activate

## Initialize development database
    ./manage.py migrate && \
    ./manage.py createsuperuser && \
    ./manage.py loaddata membership/fixtures/membership_fees.json && \
    ./manage.py generate_test_data

## Use development settings
    export SIKTEERI_CONFIGURATION=dev

## Compile translations and run development server
    ./run-sikteeri.sh

## Access the development server at
    http://127.0.0.1:8000/

## Log in at
    http://127.0.0.1:8000/login/

## Run unit tests (always before committing changes)
    ./manage.py test

### OR with py.test:
    pip install pytest pytest-cov pytest-django
    ./test.sh

## Settings
If you want to override settings, create a local settings
file which has "import * from sikteeri.settings" and set:

    export DJANGO_SETTINGS_MODULE=sikteeri.my_settings

The default settings.py must be the default development
configuration and work out of the box for quick development.
Production settings (email subjects, bank account numbers
etc.) are configured as JSON file.

Docker
======

To make development easier there exists a `Dockerfile` to use as a development container.

To build a new version:

`docker build -t sikteeri .`

To run it:

`docker run -ditp 8080:8080 --name sikteeri sikteeri`

To run it with bash as initial command:

`docker run -itp 8080:8080 --name sikteeri sikteeri /bin/bash`

To attach to Django std feed:

`docker attach sikteeri`

To attach a shell to a running instance:

`docker exec -it sikteeri /bin/bash`
