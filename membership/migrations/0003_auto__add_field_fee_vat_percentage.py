# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Fee.vat_percentage'
        db.add_column('membership_fee', 'vat_percentage',
                      self.gf('django.db.models.fields.IntegerField')(default=0),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Fee.vat_percentage'
        db.delete_column('membership_fee', 'vat_percentage')


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
            'start': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime(2013, 12, 18, 0, 0)'}),
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
            'type': ('django.db.models.fields.CharField', [], {'max_length': '1'}),
            'vat_percentage': ('django.db.models.fields.IntegerField', [], {})
        },
        'membership.membership': {
            'Meta': {'object_name': 'Membership'},
            'approved': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'billing_contact': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "'billing_set'", 'null': 'True', 'to': "orm['membership.Contact']"}),
            'birth_year': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'dissociated': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'dissociation_requested': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
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