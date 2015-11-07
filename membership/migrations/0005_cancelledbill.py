# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('membership', '0004_make_phone_optional'),
    ]

    operations = [
        migrations.CreateModel(
            name='CancelledBill',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Created')),
                ('exported', models.BooleanField(default=False)),
                ('bill', models.OneToOneField(verbose_name='Original bill', to='membership.Bill')),
            ],
        ),
    ]
