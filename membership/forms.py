# -*- coding: utf-8 -*-

from django import forms
from django.utils.translation import ugettext_lazy as _

from models import *

class MembershipForm(forms.Form):
    extra_info = forms.CharField(label=_('Additional information'), widget=forms.Textarea(attrs={'cols': '40'}),
                                 required=False)
    nationality = forms.CharField(max_length=30, min_length=5, label=_('Nationality'))
    municipality = forms.CharField(max_length=30, min_length=2, label=_('Home municipality'))


class BaseContactForm(forms.Form):
    street_address = forms.CharField(max_length=30, min_length=4,
                                     error_messages={'required': _('Street address required')},
                                     label=_('Street address'))
    postal_code = forms.RegexField(regex='^\d{5}$',
                                   error_messages={'required': _('Postal code required'),
                                                   'invalid': _('Postal code invalid')},
                                   label=_('Postal code'))
    
    post_office = forms.CharField(max_length=30, min_length=2, label=_('Post office'))
    country = forms.CharField(max_length=128, label=_('Country'))
    phone = forms.RegexField(regex='[\d\+-]{5,20}',
                             error_messages={'invalid': _('Phone invalid')},
                             min_length=5, max_length=20, label=_('Phone number'))
    sms = forms.RegexField(regex='[\d\+-]{5,20}',
                           error_messages={'invalid': _('SMS number invalid')},
                           min_length=5, max_length=20, label=_('SMS'))
    email = forms.EmailField(label=_('Email'))
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


#    login = UniqueAliasField(regex='^[a-z][a-z0-9_\-\.]{1,15}$',
#                             error_messages={'invalid': 'Syöttämäsi käyttäjätunnus ei kelpaa. Se on joko olemassa tai sisältää merkkejä, joita ei voi sisällyttää käyttäjätunnukseen. Vain merkit a-z, 0-9, _, - ja . kelpaavat. Tämän lisäksi tunnuksen täytyy alkaa kirjaimella.'},
#                             label='Käyttäjätunnustoive',
#                             help_text='''(sisältää sähköpostin tunnus@kapsi.fi)''',
#                             widget=forms.TextInput)

#    email_forward = forms.BooleanField(label='etunimi.sukunimi@kapsi.fi sähköpostiohjaus', required=False)
#    publish_in_list = forms.BooleanField(label='Nimeni saa näyttää julkisessa jäsenlistauksessa.', required=False,
#                                         help_text='''(etunimi ja sukunimi julkiseen, indeksoimattomaan jäsenlistaan)''')


