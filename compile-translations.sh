#!/usr/bin/env bash

NEW=$1

# If new strings have been introduced, translations need
# to be updated.
#
# Run:
#
# ./compile-translations.sh new

for i in membership sikteeri services; do
	(
		cd $i
		if [ "$1" = "new" ]; then
			django-admin.py makemessages -a
			django-admin.py makemessages -d djangojs -a
		fi
		django-admin.py compilemessages
	)
done
