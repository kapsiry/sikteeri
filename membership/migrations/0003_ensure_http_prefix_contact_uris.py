# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    def ensure_http_prefix_contact(apps, schema_editor):
        Contact = apps.get_model("membership", "Contact")
        # Contacts with broken homepage field value
        for contact in Contact.objects\
                .exclude(homepage='')\
                .exclude(homepage__startswith="http://")\
                .exclude(homepage__startswith="https://"):
            if contact.homepage:
                if ":/" not in contact.homepage:
                    contact.homepage = "http://{uri}".format(uri=contact.homepage)
                    contact.save()

    dependencies = [
        ('membership', '0002_charfields_to_not_null'),
    ]

    operations = [
        migrations.RunPython(ensure_http_prefix_contact)
    ]
