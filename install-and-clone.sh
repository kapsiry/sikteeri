#!/bin/bash

#
# Installs Django in a virtual environment and clones Hukka's repo.
#

hg -v 2>&1 > /dev/null
if [ $? != 0 ]; then
    echo "hg command not found, cannot clone virtualenv."
    exit 1
fi

git --version 2>&1 > /dev/null
if [ $? != 0 ]; then
    echo "git command not found, cannot clone repo."
    exit 1
fi


if [ -z $1 ]; then
    echo "Installs Django in a virtual environment and clones Hukka's repo."
    echo
    echo "Usage: ${0} MASTER-SIKTEERI-DIR"
    echo "MASTER-SIKTEERI-DIR is the directory where your git repo Python virtual"
    echo "                    environment reside."
    exit 0
fi


mkdir $1
cd $1
hg clone http://bitbucket.org/ianb/virtualenv/
python ./virtualenv/virtualenv.py sikteeri-env
source sikteeri-env/bin/activate
wget http://www.djangoproject.com/download/1.1.1/tarball/
tar xzf Django-1.1.1.tar.gz
cd Django-1.1.1
python setup.py install
cd ..
git clone http://koti.kapsi.fi/hukka/django-sikteeri.git
cd django-sikteeri/sikteeri
cp local_settings.py.template local_settings.py
cd ../..

p=$(pwd)
echo
echo "Cloned evelopment repository to \"${p}/django-sikteeri\"."
echo "You can run Sikteeri by running \"./manage.py runserver\" while in dir"
echo "\"${p}/django-sikteeri/sikteeri/\"."
echo "NOTE: you need to run \"source ${p}/sikteeri-env/bin/activate\" to enable"
echo "      your newly created virtual environment."
