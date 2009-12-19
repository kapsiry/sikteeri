# -*- coding: utf-8 -*-

from django import forms
from django.utils.translation import ugettext_lazy as _

from models import *

class MembershipForm(forms.ModelForm):
    class Meta:
        model = Membership
        exclude = ('status', 'created', 'accepted', 'last_changed')
