# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Contact'
        db.create_table('membership_contact', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('last_changed', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('first_name', self.gf('django.db.models.fields.CharField')(max_length=128, blank=True)),
            ('given_names', self.gf('django.db.models.fields.CharField')(max_length=128, blank=True)),
            ('last_name', self.gf('django.db.models.fields.CharField')(max_length=128, blank=True)),
            ('organization_name', self.gf('django.db.models.fields.CharField')(max_length=256, blank=True)),
            ('street_address', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('postal_code', self.gf('django.db.models.fields.CharField')(max_length=10)),
            ('post_office', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('country', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('phone', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('sms', self.gf('django.db.models.fields.CharField')(max_length=64, blank=True)),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75, blank=True)),
            ('homepage', self.gf('django.db.models.fields.URLField')(max_length=200, blank=True)),
        ))
        db.send_create_signal('membership', ['Contact'])

        # Adding model 'Membership'
        db.create_table('membership_membership', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('status', self.gf('django.db.models.fields.CharField')(default='N', max_length=1)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('approved', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
            ('last_changed', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('public_memberlist', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('municipality', self.gf('django.db.models.fields.CharField')(max_length=128, blank=True)),
            ('nationality', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('birth_year', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('organization_registration_number', self.gf('django.db.models.fields.CharField')(max_length=15, null=True, blank=True)),
            ('person', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='person_set', null=True, to=orm['membership.Contact'])),
            ('billing_contact', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='billing_set', null=True, to=orm['membership.Contact'])),
            ('tech_contact', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='tech_contact_set', null=True, to=orm['membership.Contact'])),
            ('organization', self.gf('django.db.models.fields.related.ForeignKey')(blank=True, related_name='organization_set', null=True, to=orm['membership.Contact'])),
            ('extra_info', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('locked', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal('membership', ['Membership'])

        # Adding model 'Fee'
        db.create_table('membership_fee', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=1)),
            ('start', self.gf('django.db.models.fields.DateTimeField')()),
            ('sum', self.gf('django.db.models.fields.DecimalField')(max_digits=6, decimal_places=2)),
        ))
        db.send_create_signal('membership', ['Fee'])

        # Adding model 'BillingCycle'
        db.create_table('membership_billingcycle', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('membership', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['membership.Membership'])),
            ('start', self.gf('django.db.models.fields.DateTimeField')(default=datetime.datetime(2013, 9, 28, 0, 0))),
            ('end', self.gf('django.db.models.fields.DateTimeField')()),
            ('sum', self.gf('django.db.models.fields.DecimalField')(max_digits=6, decimal_places=2)),
            ('is_paid', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('reference_number', self.gf('django.db.models.fields.CharField')(max_length=64)),
        ))
        db.send_create_signal('membership', ['BillingCycle'])

        # Adding model 'Bill'
        db.create_table('membership_bill', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('billingcycle', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['membership.BillingCycle'])),
            ('reminder_count', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('due_date', self.gf('django.db.models.fields.DateTimeField')()),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('last_changed', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('type', self.gf('django.db.models.fields.CharField')(default='E', max_length=1)),
        ))
        db.send_create_signal('membership', ['Bill'])

        # Adding model 'Payment'
        db.create_table('membership_payment', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('billingcycle', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['membership.BillingCycle'], null=True)),
            ('ignore', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('comment', self.gf('django.db.models.fields.CharField')(max_length=64, null=True)),
            ('reference_number', self.gf('django.db.models.fields.CharField')(max_length=64, blank=True)),
            ('message', self.gf('django.db.models.fields.CharField')(max_length=256, blank=True)),
            ('transaction_id', self.gf('django.db.models.fields.CharField')(unique=True, max_length=30)),
            ('payment_day', self.gf('django.db.models.fields.DateTimeField')()),
            ('amount', self.gf('django.db.models.fields.DecimalField')(max_digits=9, decimal_places=2)),
            ('type', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('payer_name', self.gf('django.db.models.fields.CharField')(max_length=64)),
            ('duplicate', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('membership', ['Payment'])

        # Adding model 'ApplicationPoll'
        db.create_table('membership_applicationpoll', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('membership', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['membership.Membership'])),
            ('date', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
            ('answer', self.gf('django.db.models.fields.CharField')(max_length=512)),
        ))
        db.send_create_signal('membership', ['ApplicationPoll'])


    def backwards(self, orm):
        # Deleting model 'Contact'
        db.delete_table('membership_contact')

        # Deleting model 'Membership'
        db.delete_table('membership_membership')

        # Deleting model 'Fee'
        db.delete_table('membership_fee')

        # Deleting model 'BillingCycle'
        db.delete_table('membership_billingcycle')

        # Deleting model 'Bill'
        db.delete_table('membership_bill')

        # Deleting model 'Payment'
        db.delete_table('membership_payment')

        # Deleting model 'ApplicationPoll'
        db.delete_table('membership_applicationpoll')


    models = {
        'membership.applicationpoll': {
            'Meta': {'object_name': 'ApplicationPoll'},
            'answer': ('django.db.models.fields.CharField', [], {'max_length': '512'}),
            'date': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'membership': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['membership.Membership']"})
        },
        'membership.bill': {
            'Meta': {'object_name': 'Bill'},
            'billingcycle': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['membership.BillingCycle']"}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'due_date': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_changed': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'reminder_count': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'type': ('django.db.models.fields.CharField', [], {'default': "'E'", 'max_length': '1'})
        },
        'membership.billingcycle': {
            'Meta': {'object_name': 'BillingCycle'},
            'end': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_paid': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'membership': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['membership.Membership']"}),
            'reference_number': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'start': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 9, 28, 0, 0)'}),
            'sum': ('django.db.models.fields.DecimalField', [], {'max_digits': '6', 'decimal_places': '2'})
        },
        'membership.contact': {
            'Meta': {'object_name': 'Contact'},
            'country': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'given_names': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'homepage': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_changed': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'organization_name': ('django.db.models.fields.CharField', [], {'max_length': '256', 'blank': 'True'}),
            'phone': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'post_office': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'postal_code': ('django.db.models.fields.CharField', [], {'max_length': '10'}),
            'sms': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'street_address': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        'membership.fee': {
            'Meta': {'object_name': 'Fee'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'start': ('django.db.models.fields.DateTimeField', [], {}),
            'sum': ('django.db.models.fields.DecimalField', [], {'max_digits': '6', 'decimal_places': '2'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '1'})
        },
        'membership.membership': {
            'Meta': {'object_name': 'Membership'},
            'approved': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'billing_contact': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'billing_set'", 'null': 'True', 'to': "orm['membership.Contact']"}),
            'birth_year': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'extra_info': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_changed': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'locked': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'municipality': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'nationality': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'organization': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'organization_set'", 'null': 'True', 'to': "orm['membership.Contact']"}),
            'organization_registration_number': ('django.db.models.fields.CharField', [], {'max_length': '15', 'null': 'True', 'blank': 'True'}),
            'person': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'person_set'", 'null': 'True', 'to': "orm['membership.Contact']"}),
            'public_memberlist': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'N'", 'max_length': '1'}),
            'tech_contact': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'tech_contact_set'", 'null': 'True', 'to': "orm['membership.Contact']"}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '1'})
        },
        'membership.payment': {
            'Meta': {'object_name': 'Payment'},
            'amount': ('django.db.models.fields.DecimalField', [], {'max_digits': '9', 'decimal_places': '2'}),
            'billingcycle': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['membership.BillingCycle']", 'null': 'True'}),
            'comment': ('django.db.models.fields.CharField', [], {'max_length': '64', 'null': 'True'}),
            'duplicate': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ignore': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'message': ('django.db.models.fields.CharField', [], {'max_length': '256', 'blank': 'True'}),
            'payer_name': ('django.db.models.fields.CharField', [], {'max_length': '64'}),
            'payment_day': ('django.db.models.fields.DateTimeField', [], {}),
            'reference_number': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'transaction_id': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'}),
            'type': ('django.db.models.fields.CharField', [], {'max_length': '64'})
        }
    }

    complete_apps = ['membership']