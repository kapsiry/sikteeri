#!/bin/sh

hg clone http://bitbucket.org/ianb/virtualenv/ tmp-virtualenv
python tmp-virtualenv/virtualenv.py env
rm -rf tmp-virtualenv
source env/bin/activate
./env/bin/easy_install django
