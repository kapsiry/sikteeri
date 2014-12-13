#!/bin/bash

for i in membership sikteeri services; do
	(cd $i && django-admin.py compilemessages)
done
