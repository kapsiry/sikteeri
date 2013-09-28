# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Service'
        db.create_table('services_service', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('servicetype', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['services.ServiceType'])),
            ('alias', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['services.Alias'], null=True)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['membership.Membership'], null=True)),
            ('data', self.gf('django.db.models.fields.CharField')(max_length=256, blank=True)),
        ))
        db.send_create_signal('services', ['Service'])

        # Adding model 'ServiceType'
        db.create_table('services_servicetype', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('servicetype', self.gf('django.db.models.fields.CharField')(unique=True, max_length=64)),
        ))
        db.send_create_signal('services', ['ServiceType'])

        # Adding model 'Alias'
        db.create_table('services_alias', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['membership.Membership'])),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=128)),
            ('account', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('comment', self.gf('django.db.models.fields.CharField')(max_length=128, blank=True)),
            ('expiration_date', self.gf('django.db.models.fields.DateTimeField')(null=True, blank=True)),
        ))
        db.send_create_signal('services', ['Alias'])


    def backwards(self, orm):
        # Deleting model 'Service'
        db.delete_table('services_service')

        # Deleting model 'ServiceType'
        db.delete_table('services_servicetype')

        # Deleting model 'Alias'
        db.delete_table('services_alias')


    models = {
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
        'services.alias': {
            'Meta': {'ordering': "['name']", 'object_name': 'Alias'},
            'account': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'comment': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'expiration_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['membership.Membership']"})
        },
        'services.service': {
            'Meta': {'object_name': 'Service'},
            'alias': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['services.Alias']", 'null': 'True'}),
            'data': ('django.db.models.fields.CharField', [], {'max_length': '256', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['membership.Membership']", 'null': 'True'}),
            'servicetype': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['services.ServiceType']"})
        },
        'services.servicetype': {
            'Meta': {'object_name': 'ServiceType'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'servicetype': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '64'})
        }
    }

    complete_apps = ['services']