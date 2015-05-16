# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    def add_servicetypes(apps, schema_editor):
        ServiceType = apps.get_model('services', 'ServiceType')

        for st in SERVICE_TYPES:
            ServiceType.objects.get_or_create(
                pk=st['pk'],
                servicetype=st['fields']['servicetype']
            )

    def del_servicetypes(apps, schema_editor):
        ServiceType = apps.get_model('services', 'ServiceType')

        for st in SERVICE_TYPES:
            ServiceType.objects.get(pk=st['pk'], servicetype=st['fields']['servicetype']).delete()

    dependencies = [
        ('services', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(add_servicetypes, del_servicetypes)
    ]


SERVICE_TYPES = [
  {
    "pk": 1,
    "model": "services.servicetype",
    "fields": {
      "servicetype": "UNIX account"
    }
  },
  {
    "pk": 2,
    "model": "services.servicetype",
    "fields": {
      "servicetype": "Email alias"
    }
  },
  {
    "pk": 3,
    "model": "services.servicetype",
    "fields": {
      "servicetype": "WWW vhost"
    }
  },
  {
    "pk": 4,
    "model": "services.servicetype",
    "fields": {
      "servicetype": "MySQL database"
    }
  },
  {
    "pk": 5,
    "model": "services.servicetype",
    "fields": {
      "servicetype": "PostgreSQL database"
    }
  },
  {
    "pk": 6,
    "model": "services.servicetype",
    "fields": {
      "servicetype": "DNS domain"
    }
  },
  {
    "pk": 7,
    "model": "services.servicetype",
    "fields": {
      "servicetype": "IRC vhost"
    }
  },
  {
    "pk": 8,
    "model": "services.servicetype",
    "fields": {
      "servicetype": "SVN repository"
    }
  },
  {
    "pk": 9,
    "model": "services.servicetype",
    "fields": {
      "servicetype": "Mailbox account"
    }
  },
  {
    "pk": 10,
    "model": "services.servicetype",
    "fields": {
      "servicetype": "Firewall port"
    }
  }
]
