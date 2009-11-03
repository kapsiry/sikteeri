# -*- coding: utf-8 -*-

from django import forms
from django.utils.translation import ugettext_lazy as _

from models import *

class MembershipForm(forms.ModelForm):
    def clean(self):
        data = self.cleaned_data
        if data.get('organization_name'):
            if data.get('given_name') or data.get('first_names') or data.get('last_name'):
                raise forms.ValidationError(_("You can't supply both an organization name and a private name"))
        else:
            if not data.get('given_name') or not data.get('first_names') or not data.get('last_name'):
                raise forms.ValidationError(_("You have to give a given name, all first names and surname."))
        return data
    class Meta:
        model = Membership
        exclude = ('status', 'created', 'accepted', 'last_changed')
