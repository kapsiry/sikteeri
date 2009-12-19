#!/bin/sh

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
    ./manage.py loaddata test_data.json || fail "Loading test data failed"
fi

./manage.py runserver || fail "Starting server failed"
