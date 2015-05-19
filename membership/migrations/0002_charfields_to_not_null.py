# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('membership', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='billingcycle',
            name='start',
            field=models.DateTimeField(default=django.utils.timezone.now, verbose_name='Start'),
        ),
        migrations.AlterField(
            model_name='membership',
            name='organization_registration_number',
            field=models.CharField(default='', max_length=15, verbose_name='Organization registration number', blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='payment',
            name='comment',
            field=models.CharField(default='', max_length=64, verbose_name='Comment', blank=True),
            preserve_default=False,
        ),
    ]
