# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.files.storage
import datetime


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='ApplicationPoll',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('date', models.DateTimeField(auto_now=True, verbose_name='Timestamp')),
                ('answer', models.CharField(max_length=512, verbose_name='Service specific data')),
            ],
        ),
        migrations.CreateModel(
            name='Bill',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('reminder_count', models.IntegerField(default=0, verbose_name='Reminder count')),
                ('due_date', models.DateTimeField(verbose_name='Due date')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Created')),
                ('last_changed', models.DateTimeField(auto_now=True, verbose_name='Last changed')),
                ('pdf_file', models.FileField(storage=django.core.files.storage.FileSystemStorage(location=b'cache'), null=True, upload_to=b'bill_pdfs')),
                ('type', models.CharField(default=b'E', max_length=1, verbose_name='Bill type', choices=[(b'E', 'Email'), (b'P', 'Paper'), (b'S', 'SMS')])),
            ],
        ),
        migrations.CreateModel(
            name='BillingCycle',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('start', models.DateTimeField(default=datetime.datetime(2015, 5, 17, 0, 32, 53, 953781), verbose_name='Start')),
                ('end', models.DateTimeField(verbose_name='End')),
                ('sum', models.DecimalField(verbose_name='Sum', max_digits=6, decimal_places=2)),
                ('is_paid', models.BooleanField(default=False, verbose_name='Is paid')),
                ('reference_number', models.CharField(max_length=64, verbose_name='Reference number')),
            ],
            options={
                'permissions': (('read_bills', 'Can read billing details'), ('manage_bills', 'Can manage billing')),
            },
        ),
        migrations.CreateModel(
            name='Contact',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('last_changed', models.DateTimeField(auto_now=True, verbose_name='contact changed')),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='contact created')),
                ('first_name', models.CharField(max_length=128, verbose_name='First name', blank=True)),
                ('given_names', models.CharField(max_length=128, verbose_name='Given names', blank=True)),
                ('last_name', models.CharField(max_length=128, verbose_name='Last name', blank=True)),
                ('organization_name', models.CharField(max_length=256, verbose_name='Organization name', blank=True)),
                ('street_address', models.CharField(max_length=128, verbose_name='Street address')),
                ('postal_code', models.CharField(max_length=10, verbose_name='Postal code')),
                ('post_office', models.CharField(max_length=128, verbose_name='Post office')),
                ('country', models.CharField(max_length=128, verbose_name='Country')),
                ('phone', models.CharField(max_length=64, verbose_name='Phone')),
                ('sms', models.CharField(max_length=64, verbose_name='SMS number', blank=True)),
                ('email', models.EmailField(max_length=254, verbose_name='E-mail', blank=True)),
                ('homepage', models.URLField(verbose_name='Homepage', blank=True)),
            ],
        ),
        migrations.CreateModel(
            name='Fee',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.CharField(max_length=1, verbose_name='Fee type', choices=[(b'P', 'Person'), (b'S', 'Supporting'), (b'O', 'Organization'), (b'H', 'Honorary')])),
                ('start', models.DateTimeField(verbose_name='Valid from date')),
                ('sum', models.DecimalField(verbose_name='Sum', max_digits=6, decimal_places=2)),
                ('vat_percentage', models.IntegerField(verbose_name='VAT percentage')),
            ],
        ),
        migrations.CreateModel(
            name='Membership',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('type', models.CharField(max_length=1, verbose_name='Membership type', choices=[(b'P', 'Person'), (b'S', 'Supporting'), (b'O', 'Organization'), (b'H', 'Honorary')])),
                ('status', models.CharField(default=b'N', max_length=1, verbose_name='Membership status', choices=[(b'N', 'New'), (b'P', 'Pre-approved'), (b'A', 'Approved'), (b'S', 'Dissociation requested'), (b'I', 'Dissociated'), (b'D', 'Deleted')])),
                ('created', models.DateTimeField(auto_now_add=True, verbose_name='Membership created')),
                ('approved', models.DateTimeField(null=True, verbose_name='Membership approved', blank=True)),
                ('last_changed', models.DateTimeField(auto_now=True, verbose_name='Membership changed')),
                ('public_memberlist', models.BooleanField(default=False, verbose_name='Show in the memberlist')),
                ('municipality', models.CharField(max_length=128, verbose_name='Home municipality', blank=True)),
                ('nationality', models.CharField(max_length=128, verbose_name='Nationality')),
                ('birth_year', models.IntegerField(null=True, verbose_name='Year of birth', blank=True)),
                ('organization_registration_number', models.CharField(max_length=15, null=True, verbose_name='Organization registration number', blank=True)),
                ('extra_info', models.TextField(verbose_name='Additional information', blank=True)),
                ('locked', models.DateTimeField(null=True, verbose_name='Membership locked', blank=True)),
                ('dissociation_requested', models.DateTimeField(null=True, verbose_name='Dissociation requested', blank=True)),
                ('dissociated', models.DateTimeField(null=True, verbose_name='Member dissociated', blank=True)),
                ('billing_contact', models.ForeignKey(related_name='billing_set', verbose_name='Billing contact', blank=True, to='membership.Contact', null=True)),
                ('organization', models.ForeignKey(related_name='organization_set', verbose_name='Organization', blank=True, to='membership.Contact', null=True)),
                ('person', models.ForeignKey(related_name='person_set', verbose_name='Person', blank=True, to='membership.Contact', null=True)),
                ('tech_contact', models.ForeignKey(related_name='tech_contact_set', verbose_name='Technical contact', blank=True, to='membership.Contact', null=True)),
            ],
            options={
                'permissions': (('read_members', 'Can read member details'), ('manage_members', 'Can change details, pre-/approve'), ('delete_members', 'Can delete members'), ('dissociate_members', 'Can dissociate members'), ('request_dissociation_for_member', 'Can request dissociation for member')),
            },
        ),
        migrations.CreateModel(
            name='Payment',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('ignore', models.BooleanField(default=False, verbose_name='Ignored payment')),
                ('comment', models.CharField(max_length=64, null=True, verbose_name='Comment')),
                ('reference_number', models.CharField(max_length=64, verbose_name='Reference number', blank=True)),
                ('message', models.CharField(max_length=256, verbose_name='Message', blank=True)),
                ('transaction_id', models.CharField(unique=True, max_length=30, verbose_name='Transaction id')),
                ('payment_day', models.DateTimeField(verbose_name='Payment day')),
                ('amount', models.DecimalField(verbose_name='Amount', max_digits=9, decimal_places=2)),
                ('type', models.CharField(max_length=64, verbose_name='Type')),
                ('payer_name', models.CharField(max_length=64, verbose_name='Payer name')),
                ('duplicate', models.BooleanField(default=False, verbose_name='Duplicate payment')),
                ('billingcycle', models.ForeignKey(verbose_name='Cycle', to='membership.BillingCycle', null=True)),
            ],
            options={
                'permissions': (('can_import_payments', 'Can import payment data'),),
            },
        ),
        migrations.AddField(
            model_name='billingcycle',
            name='membership',
            field=models.ForeignKey(verbose_name='Membership', to='membership.Membership'),
        ),
        migrations.AddField(
            model_name='bill',
            name='billingcycle',
            field=models.ForeignKey(verbose_name='Cycle', to='membership.BillingCycle'),
        ),
        migrations.AddField(
            model_name='applicationpoll',
            name='membership',
            field=models.ForeignKey(verbose_name='Membership', to='membership.Membership'),
        ),
    ]
