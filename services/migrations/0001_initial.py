# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('membership', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Alias',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=128, verbose_name='Alias name')),
                ('account', models.BooleanField(default=False, verbose_name='Is UNIX account')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Created')),
                ('comment', models.CharField(max_length=128, verbose_name='Comment', blank=True)),
                ('expiration_date', models.DateTimeField(null=True, verbose_name='Alias expiration date', blank=True)),
                ('owner', models.ForeignKey(verbose_name='Alias owner', to='membership.Membership')),
            ],
            options={
                'ordering': ['name'],
                'verbose_name_plural': 'aliases',
                'permissions': (('manage_aliases', 'Can manage aliases'),),
            },
        ),
        migrations.CreateModel(
            name='Service',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('data', models.CharField(max_length=256, verbose_name='Service specific data', blank=True)),
                ('alias', models.ForeignKey(verbose_name='Related alias', to='services.Alias', null=True)),
                ('owner', models.ForeignKey(verbose_name='Service owner', to='membership.Membership', null=True)),
            ],
            options={
                'permissions': (('can_manage_services', 'Can manage member services'),),
            },
        ),
        migrations.CreateModel(
            name='ServiceType',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('servicetype', models.CharField(unique=True, max_length=64, verbose_name='Service type')),
            ],
            options={
                'permissions': (('can_manage_servicetypes', 'Can manage available service types'),),
            },
        ),
        migrations.AddField(
            model_name='service',
            name='servicetype',
            field=models.ForeignKey(verbose_name='Service type', to='services.ServiceType'),
        ),
    ]
