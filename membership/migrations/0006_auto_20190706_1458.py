# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2019-07-06 14:58
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('membership', '0005_cancelledbill'),
    ]

    operations = [
        migrations.AddField(
            model_name='membership',
            name='dissociation_pending_until',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Dissociation pending until'),
        ),
    ]
