# -*- coding: utf-8 -*-

from django import forms
from django.utils.translation import ugettext_lazy as _

from models import *

class PersonMembershipForm(forms.Form):
    nationality = forms.CharField(max_length=30, min_length=5,
                                  label=_('Nationality'),
                                  initial=_('Finnish nationality'),
                                  help_text=_('Your nationality'))
    municipality = forms.CharField(max_length=30, min_length=2,
                                   label=_('Home municipality'),
                                   help_text=_('Place of residence'))
    extra_info = forms.CharField(label=_('Additional information'),
                                 widget=forms.Textarea(attrs={'cols': '40'}),
                                 required=False,
                                 help_text=_('You can write additional questions or details here'))

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
                                 help_text=_('You can write additional questions or details here'))

class BaseContactForm(forms.Form):
    street_address = forms.CharField(max_length=30, min_length=4,
                                     error_messages={'required': _('Street address required')},
                                     label=_('Street address'))
    postal_code = forms.RegexField(regex='^\d{5}$',
                                   error_messages={'required': _('Postal code required'),
                                                   'invalid': _('Postal code invalid')},
                                   label=_('Postal code'))
    
    post_office = forms.CharField(max_length=30, min_length=2, label=_('Post office'))
    country = forms.CharField(max_length=128, label=_('Country'), initial=_('Finland'))
    phone = forms.RegexField(regex='[\d\+-]{5,20}',
                             error_messages={'invalid': _('Phone invalid')},
                             min_length=5, max_length=20, label=_('Phone number'),
                             help_text=_('Phone number that accepts calls'))
    sms = forms.RegexField(regex='[\d\+-]{5,20}',
                           error_messages={'invalid': _('SMS number invalid')},
                           min_length=5, max_length=20, label=_('SMS number'),
                           help_text=_('Phone number that accepts text messages'))
    email = forms.EmailField(label=_('E-mail'))
    homepage = forms.URLField(required=False, label=_('Homepage'))

class PersonBaseContactForm(forms.Form):
    first_name = forms.CharField(max_length=40, min_length=1,
                                 error_messages={'required': _('First name required')},
                                 label=_('First name'))
    given_names = forms.CharField(max_length=30, min_length=2,
                                  error_messages={'required': _('Given names required')},
                                  label=_('Given names'))
    last_name = forms.CharField(max_length=30, min_length=2,
                                error_messages={'required': _('Last name required')},
                                label=_('Last name'))

class OrganizationBaseContactForm(forms.Form):
    organization_name = forms.CharField(max_length=50, label=_('Organization name'))


class PersonContactForm(PersonBaseContactForm, BaseContactForm):
    pass

class OrganizationContactForm(OrganizationBaseContactForm, BaseContactForm):
    pass


class PersonApplicationForm(PersonContactForm, PersonMembershipForm):
    pass

class OrganizationApplicationForm(OrganizationContactForm, OrganizationMembershipForm):
    pass
