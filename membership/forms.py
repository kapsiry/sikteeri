# -*- coding: utf-8 -*-

from django import forms
from django.utils.translation import ugettext_lazy as _

from models import *

class MembershipForm(forms.Form):
    extra_info = forms.CharField(label=_('info'), widget=forms.Textarea(attrs={'cols': '80'}),
                                 required=False)
    nationality = forms.CharField(max_length=30, min_length=5, label=_('nationality'))
    municipality = forms.CharField(max_length=30, min_length=2, label=_('municipality'))


class BaseContactForm(forms.Form):
    street_address = forms.CharField(max_length=30, min_length=4,
                                     error_messages={'required': _('street address required')},
                                     label=_('street address'))
    postal_code = forms.RegexField(regex='^\d{5}$',
                                   error_messages={'required': _('postal code required'),
                                                   'invalid': 'postal code invalid'},
                                   label=_('postal code'))
    
    post_office = forms.CharField(max_length=30, min_length=2, label=_('post office'))
    country = forms.CharField(max_length=128, label=_('country'))
    phone = forms.RegexField(regex='[\d\+-]{5,20}',
                             error_messages={'invalid': _('phone invalid')},
                             min_length=5, max_length=20, label=_('phone number'))
    sms = forms.RegexField(regex='[\d\+-]{5,20}',
                           error_messages={'invalid': _('sms invalid')},
                           min_length=5, max_length=20, label=_('sms'))
    email = forms.EmailField(label=_('email'))
    homepage = forms.URLField(required=False, label=_('homepage'))

class PersonBaseContactForm(forms.Form):
    first_name = forms.CharField(max_length=40, min_length=1,
                                 error_messages={'required': _('first name required')},
                                 label=_('first name'))
    given_names = forms.CharField(max_length=30, min_length=2,
                                  error_messages={'required': _('given names required')},
                                  label=_('given names'))
    last_name = forms.CharField(max_length=30, min_length=2,
                                error_messages={'required': _('last name required')},
                                label=_('last name'))

class OrganizationBaseContactForm(forms.Form):
    organization_name = forms.CharField(max_length=50, label=_('organization name'))


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


