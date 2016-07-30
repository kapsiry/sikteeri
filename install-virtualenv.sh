#!/usr/bin/env bash

# install-virtualenv.sh
#
# Install virtualenv environment for sikteeri development
# to "~/env/sikteeri" if it doesn't exist already
# Feel free to create virtualenv manually if you prefer.

VIRTUALENV=${1-virtualenv}
ENVDIR="env"

function fatal () {
    echo $*
    exit 1
}

# Check requirements
type "$VIRTUALENV" >/dev/null 2>&1 || fatal "Python virtualenv required. Maybe pip install virtualenv?"
test -a "$ENVDIR" && fatal "$ENVDIR already exists"

# Prepare virtualenv
(
    set -x
    "$VIRTUALENV" --python=python2.7 "$ENVDIR" --no-site-packages || fatal "Failed to create virtualenv $ENVDIR"
)

# OS X: Use homebrew gettext if no system gettext installed
(
    [[ `uname` == "Darwin" ]] || exit   # Only on OS X
    type msgfmt >/dev/null 2>&1 && exit # skip if msgfmt in path
    # If we can find homebrew gettext, use that instead
    if [ -f "$(brew --prefix gettext)/bin/msgfmt" ]; then
        set -x
        echo "export PATH=\"\$PATH:$(brew --prefix gettext)/bin\"" >> "$ENVDIR/bin/activate"
    fi
)


# In virtualenv target
source "${ENVDIR}/bin/activate"
(
    echo "In virtualenv $ENVDIR"
    set -x
    pip install --quiet -r requirements.txt
)


echo "Virtualenv environment $ENVDIR done"
echo "To later activate the environment, type"
echo "  source ${ENVDIR}/bin/activate"
exit 0
