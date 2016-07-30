#!/usr/bin/env bash

fail () {
    echo $@
    exit 1
}


# Run in virtualenv

# Path to virtualenv
# default "env" or environment variable VIRTUALENV

ENV="${VIRTUALENV:-env}"

test -r "${ENV}/bin/activate" || fail "Virtualenv required in $ENV"

# Build translations
./compile-translations.sh

./manage.py runserver "$@"
