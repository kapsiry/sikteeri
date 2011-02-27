# -*- coding: utf-8 -*-

import re
import logging
from django import forms
from django.utils.translation import ugettext_lazy as _

from utils import log_change
from models import *
from services.models import Alias

class LoginField(forms.CharField):
    def __init__(self, *args, **kwargs):
        super(LoginField, self).__init__(min_length=2, max_length=16, *args, **kwargs)

    def clean(self, value):
        super(LoginField, self).clean(value)

        errors = []
        if re.match(r"^[a-z][a-z0-9._-]*$", value) == None:
            errors.append(_('Login begins with an illegal character or contains an illegal character.'))
        if Alias.objects.filter(name__iexact=value).count() > 0:
            errors.append(_('Login already reserved.'))

        if len(errors) > 0:
            raise forms.ValidationError(errors)

        return value


class PersonMembershipForm(forms.Form):
    nationality = forms.CharField(max_length=30, min_length=5,
                                  label=_('Nationality'),
                                  initial=_('Finnish nationality'),
                                  help_text=_('Your nationality'))
    municipality = forms.CharField(max_length=30, min_length=2,
                                   label=_('Home municipality'),
                                   help_text=_(u'Home municipality in the population information system. If it\'s abroad, write it in the form of “Municipality, country”.'))
    extra_info = forms.CharField(label=_('Additional information'),
                                 widget=forms.Textarea(attrs={'cols': '40'}),
                                 required=False,
                                 help_text=_('You can write additional questions or details here'),
                                 max_length=1000)

    email_forward = forms.CharField(min_length=2)
    public_memberlist = forms.BooleanField(label=_('My name (first and last name) and homepage can be shown in the public memberlist'), required=False)

class ServiceForm(forms.Form):
    mysql_database = forms.BooleanField(label=_('I want a MySQL database'), required=False)
    postgresql_database = forms.BooleanField(label=_('I want a PostgreSQL database'), required=False)
    login_vhost = forms.BooleanField(label=_('I want a login.kapsi.fi website'), required=False)
    unix_login = LoginField(label=_('UNIX Login'))

class OrganizationMembershipForm(forms.Form):
    nationality = forms.CharField(max_length=30, min_length=5,
                                  label=_('Nationality'),
                                  initial=_('Finnish nationality'),
                                  help_text=_('Home country of your organization'))
    municipality = forms.CharField(max_length=30, min_length=2,
                                   label=_('Home municipality'),
                                   help_text=_('Place where your organization is registered to'))
    extra_info = forms.CharField(label=_('Additional information'),
                                 widget=forms.Textarea(attrs={'cols': '40'}),
                                 required=False,
                                 help_text=_('You can write additional questions or details here'),
                                 max_length=1000)
    public_memberlist = forms.BooleanField(label=_('Organization information (name and homepage) can be shown in the public memberlist'), required=False)

class BaseContactForm(forms.Form):
    street_address = forms.CharField(max_length=30, min_length=4,
                                     error_messages={'required': _('Street address required.')},
                                     label=_('Street address'))
    postal_code = forms.RegexField(regex='^[a-z0-9-]{2,10}$',
                                   error_messages={'required': _('Postal code required.')},
                                   label=_('Postal code'))
    
    post_office = forms.CharField(max_length=30, min_length=2, label=_('Post office'))
    country = forms.CharField(max_length=128, label=_('Country'), initial=_('Finland'))
    phone = forms.RegexField(regex='[\d\+-]{5,20}',
                             error_messages={'invalid': _('Phone invalid.')},
                             min_length=5, max_length=20, label=_('Phone number'),
                             help_text=_('Phone number that accepts calls'))
    sms = forms.RegexField(regex='[\d\+-]{5,20}',
                           error_messages={'invalid': _('SMS number invalid.')},
                           min_length=5, max_length=20, label=_('SMS number'),
                           help_text=_('Phone number that accepts text messages'))
    email = forms.EmailField(label=_('E-mail'))
    homepage = forms.URLField(required=False,
                              label=_('Homepage'),
                              help_text=_('Homepage for the public member list'))

    def clean(self):
        if self.cleaned_data.has_key('postal_code') and (self.cleaned_data['country'] == 'Finland' or
                                                         self.cleaned_data['country'] == 'Suomi'):
            if re.match(r"^[\d]{5}$", self.cleaned_data['postal_code']) == None:
                self._errors["postal_code"] = self.error_class([_("Postal codes in Finland must consist of 5 numbers.")])
                del self.cleaned_data["postal_code"]
        return self.cleaned_data

class PersonBaseContactForm(forms.Form):
    first_name = forms.CharField(max_length=40, min_length=1,
                                 error_messages={'required': _('First name required.')},
                                 label=_('First name'),
                                 help_text=_('First name or preferred given name'))
    given_names = forms.CharField(max_length=30, min_length=2,
                                  error_messages={'required': _('Given names required.')},
                                  label=_('Given names'),
                                  help_text=_('Including first name'))
    last_name = forms.CharField(max_length=30, min_length=2,
                                error_messages={'required': _('Last name required.')},
                                label=_('Last name'))

class OrganizationBaseContactForm(forms.Form):
    organization_name = forms.CharField(max_length=50, min_length=6, label=_('Organization name'))

class PersonContactForm(PersonBaseContactForm, BaseContactForm):
    pass

class OrganizationContactForm(OrganizationBaseContactForm, BaseContactForm):
    pass

class PersonApplicationForm(PersonContactForm, PersonMembershipForm, ServiceForm):
    pass
       
class OrganizationApplicationForm(OrganizationContactForm, OrganizationMembershipForm):
    pass
