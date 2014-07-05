#!/bin/bash

fail () {
    echo $@
    exit 1
}


# Run in virtualenv
ENV="$HOME/env/sikteeri"
test -r "${ENV}/bin/activate" || fail "Virtualenv required in $ENV"

# Build translations
./compile-translations.sh

./manage.py runserver "$@"
