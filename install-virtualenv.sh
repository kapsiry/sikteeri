#!/bin/bash

# install-virtualenv.sh
#
# Install virtualenv environment for sikteeri development
# to "env/" if it doesn't exist already

VIRTUALENV=${1-virtualenv}
ENVDIR=env

if [[ ! -x "$VIRTUALENV" ]]; then
	VIRTUALENV=`which $VIRTUALENV`
fi

if [[ ! -x "$VIRTUALENV" ]]; then

    echo "Please install virtualenv first."
    echo
    echo "  sudo apt-get install python-virtualenv (Debian/Ubuntu)"
    echo "  sudo easy_install virtualenv (OS X, others?)"
    echo
    echo "If you have installed it already, try running"
    echo
    echo "$(basename $0) <path-to-virtualenv>"
    exit 1
fi

function fatal () {
    echo $*
    exit 1
}

test -a $ENVDIR && fatal "$ENVDIR already exists"

$VIRTUALENV $ENVDIR || fatal "Failed to create virtualenv $ENVDIR"

source $ENVDIR/bin/activate

if [[ ! -a $ENVDIR/bin/pip ]]; then
    $ENVDIR/bin/easy_install pip || fatal "Could not install pip in virtualenv"
fi

for pkg in django simplejson; do
    $ENVDIR/bin/pip install $pkg || fatal "Could not install $pkg in $ENVDIR"
done

echo "export PYTHONPATH=.." >> $ENVDIR/bin/activate

echo "Virtualenv environment $ENVDIR done"
echo "To later activate the environment, type"
echo "  . env/bin/activate"
exit 0
