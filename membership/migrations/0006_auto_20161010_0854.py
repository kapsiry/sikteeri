# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('membership', '0005_cancelledbill'),
    ]

    operations = [
        migrations.AlterField(
            model_name='payment',
            name='transaction_id',
            field=models.CharField(max_length=35, verbose_name='Transaction id'),
        ),
        migrations.AlterUniqueTogether(
            name='payment',
            unique_together=set([('reference_number', 'transaction_id', 'message')]),
        ),
    ]
