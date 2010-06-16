#!/bin/bash

for i in membership sikteeri ; do
	(cd $i && django-admin.py compilemessages)
done
