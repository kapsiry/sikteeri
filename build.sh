#!/bin/sh

for i in membership sikteeri ; do
	(cd $i && django-admin.py compilemessages)
done
