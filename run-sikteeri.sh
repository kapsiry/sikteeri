#!/bin/bash

fail () {
    echo $@
    exit 1
}


# Run in virtualenv
ENV="$HOME/env/sikteeri"
test -r "${ENV}/bin/activate" || fail "Virtualenv required in $ENV"

PORT=${1-8000}

# Build translations
./build.sh

cd sikteeri

gunicorn_django -b 127.0.0.1:$PORT || fail "Starting server failed"

