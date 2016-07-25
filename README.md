# Sikteeri membership management service
<a href="https://codecov.io/github/kapsiry/sikteeri?branch=master">
  <img src="https://codecov.io/github/kapsiry/sikteeri/coverage.svg?branch=master" alt="Coverage via Codecov" />
</a>
<a href="https://travis-ci.org/kapsiry/sikteeri">
  <img src="https://travis-ci.org/kapsiry/sikteeri.svg?branch=master" alt="Build Status">
</a>

REQUIREMENTS
============

* Python 3.4
* gettext
* openldap and sasl dev for LDAP support

For production, additionally:
* gunicorn
* PostgreSQL

HOW TO RUN
==========

    # Create virtualenv environment
    ./install-virtualenv.sh

    # Activate virtualenv
    source env/bin/activate

    # Initialize development database
    ./manage.py migrate && \
    ./manage.py createsuperuser && \
    ./manage.py loaddata membership/fixtures/membership_fees.json && \
    ./manage.py generate_test_data

    # Compile translations and run development server
    ./run-sikteeri.sh

Access the development server at <a href="http://127.0.0.1:8000/">http://127.0.0.1:8000/</a>

Log in at <a href="http://127.0.0.1:8000/login/">http://127.0.0.1:8000/login/</a>

# Run tests

You should always run tests before committing changes.

    ./manage.py test

OR with py.test: (requires pip install pytest pytest-cov pytest-django)

    ./test.sh
