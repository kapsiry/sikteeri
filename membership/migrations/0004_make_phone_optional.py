# -*- coding: utf-8 -*-


from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('membership', '0003_ensure_http_prefix_contact_uris'),
    ]

    operations = [
        migrations.AlterField(
            model_name='contact',
            name='phone',
            field=models.CharField(max_length=64, verbose_name='Phone', blank=True),
        ),
    ]
