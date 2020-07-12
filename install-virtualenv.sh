#!/usr/bin/env bash
# Install virtualenv environment for sikteeri development
# Feel free to create virtualenv manually if you prefer.

VIRTUALENV="virtualenv"
ENVDIR="env"

# Exit on errors
set -e

function fatal () {
    echo $*
    exit 1
}

# Check requirements
###########################
# A working virtualenv command is required
"$VIRTUALENV" --version >/dev/null || fatal "Python virtualenv required. Maybe pip install virtualenv?"

# Target virtualenv directory should not exist
if [[ -a "$ENVDIR" ]]; then
    fatal "$ENVDIR already exists"
fi

# Prepare virtualenv
#############################
"$VIRTUALENV" --python=python3 "$ENVDIR" --no-site-packages || fatal "Failed to create virtualenv $ENVDIR"

# OS X specific fixes
if [[ `uname -s` == "Darwin" ]]; then
    # Fix python-ldap compilation due to missing sasl.h
    export CFLAGS="-I$(xcrun --show-sdk-path)/usr/include/sasl"

    # Fix psycopg2 build; link against homebrew installed openssl if available
    export LDFLAGS="-I/usr/local/opt/openssl/include -L/usr/local/opt/openssl/lib"

    # Add homebrew gettext to path in activate script if no system gettext installed
    if ! hash msgfmt 2>/dev/null; then
        # If we can find homebrew gettext, activate it in bin/activate script
        if [[ -f "$(brew --prefix gettext)/bin/msgfmt" ]]; then
            echo "export PATH=\"\$PATH:$(brew --prefix gettext)/bin\"" >> "$ENVDIR/bin/activate"
        fi
    fi

fi

# In virtualenv target
echo "In virtualenv $ENVDIR"
"${ENVDIR}/bin/pip" install -r requirements.txt

echo "Virtualenv environment $ENVDIR done"
echo "To activate the environment, type"
echo "  source ${ENVDIR}/bin/activate"

exit 0
