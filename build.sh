#!/bin/sh

for i in membership sikteeri ; do
	(cd $i && django-admin.py makemessages -a)
	(cd $i && django-admin.py compilemessages)
done
