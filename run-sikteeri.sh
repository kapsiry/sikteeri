#!/bin/bash

# Run in virtualenv
test -r env/bin/activate && . env/bin/activate

PORT=$1

fail () {
    echo $@
    exit 1
}

test -r sikteeri/local_settings.py || fail "sikteeri/local_settings.py not found"
export PYTHONPATH=`pwd`

# Build translations
./build.sh

cd sikteeri

if [ -r sikteeri_test.sqlite ]; then
    ./manage.py syncdb || fail "Updating database failed"
else
    ./manage.py syncdb || fail "Creating database failed"
    ./manage.py loaddata membership_fees.json || fail "Loading test data failed"
fi

if [[ -z $PORT ]]; then
    PORT=12765
fi

gunicorn_django -b 127.0.0.1:$PORT || fail "Starting server failed"

