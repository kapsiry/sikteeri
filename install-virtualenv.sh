#!/bin/bash

# install-virtualenv.sh
#
# Install virtualenv environment for sikteeri development
# to "~/env/sikteeri" if it doesn't exist already
# Feel free to create virtualenv manually if you prefer.

VIRTUALENV=${1-virtualenv}
ENVDIR="$HOME/env/sikteeri"

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
    [[ `uname` == "Darwin" ]] || exit
    # Do nothing if msgfmt in path
    type msgfmt >/dev/null 2>&1 && exit
    # If we can find homebrew gettext, use that instead
    test -a /usr/local/Cellar/gettext || exit
    gettext_brew_version=$(ls -t1 /usr/local/Cellar/gettext/ | head -n1)
    gettext_brew_path="/usr/local/Cellar/gettext/${gettext_brew_version}/bin"
    echo "export PATH=\"\$PATH:${gettext_brew_path}\"" >> "$ENVDIR/bin/activate"
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
echo "  source ~/env/bin/activate"
exit 0
