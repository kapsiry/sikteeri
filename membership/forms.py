# -*- coding: utf-8 -*-

import re
from django import forms
from django.utils.translation import ugettext_lazy as _

from services.models import Alias
from membership.models import Contact

from datetime import datetime

# User login format validation regex
VALID_USERNAME_RE = r"^[a-z][a-z0-9_]*[a-z0-9]$"

MAX_AGE = 80


class LoginField(forms.CharField):
    def __init__(self, *args, **kwargs):
        super(LoginField, self).__init__(min_length=2, max_length=16, *args, **kwargs)

    def clean(self, value):
        super(LoginField, self).clean(value)
        value = value.lower()

        errors = []
        if re.match(VALID_USERNAME_RE, value) is None:
            errors.append(_('Login begins with an illegal character or contains an illegal character.'))
        if Alias.objects.filter(name__iexact=value).count() > 0:
            errors.append(_('Login already reserved.'))

        if len(errors) > 0:
            raise forms.ValidationError(errors)

        return value


class PhoneNumberField(forms.RegexField):
    def __init__(self, *args, **kwargs):
        super(PhoneNumberField, self).__init__(regex=r"^ *[+0(][-+\d ()]{5,20} *$",
                                               min_length=4, max_length=20, *args, **kwargs)

    def clean(self, value):
        return super(PhoneNumberField, self).clean(value)\
            .replace("(", "").replace(")", "").replace(" ", "").replace("-", "")


class OrganizationRegistrationNumber(forms.RegexField):
    def __init__(self, *args, **kwargs):
        super(OrganizationRegistrationNumber, self).__init__(regex=r"^ *[\d]{7}-?\d *$",
                                                             min_length=8, max_length=20, *args, **kwargs)

    def clean(self, value):
        return super(OrganizationRegistrationNumber, self).clean(value).replace(" ", "")


class YearOfBirthField(forms.RegexField):
    def __init__(self, *args, **kwargs):
        super(YearOfBirthField, self).__init__(regex=r"^(1[9]|2[01])\d\d$",
                                               min_length=4, max_length=4, *args, **kwargs)
    
    def clean(self, value):
        c = super(YearOfBirthField, self).clean(value)
        try:
            c = int(c)
            if c > datetime.now().year:
                raise forms.ValidationError(_('Invalid year of birth'))
        except ValueError:
            raise forms.ValidationError(_('Invalid year of birth'))
        return c


class PersonMembershipInfoForm(forms.Form):
    nationality = forms.CharField(max_length=30, min_length=5,
                                  label=_('Nationality'),
                                  initial=_('Finnish nationality'),
                                  help_text=_('Your nationality'))
    municipality = forms.CharField(max_length=30, min_length=2,
                                   label=_('Home municipality'),
                                   help_text=_('Finnish municipality'))
    birth_year = YearOfBirthField(label=_("Year of birth"),
                                  help_text=_('Year of birth on format YYYY'),
                                  required=True)
    extra_info = forms.CharField(label=_('Additional information'),
                                 widget=forms.Textarea(attrs={'cols': '40'}),
                                 required=False,
                                 help_text=_('You can write additional questions or details here'),
                                 max_length=1000)

    CHOICES = (('friend', _('From friend'),),('irc', _('From IRC'),),
               ('some',_('From social media'),),('advertisement',_('From advertisement')),
               ('event', _('From event')),('other', _('Other, what?')))
    poll = forms.ChoiceField(widget=forms.RadioSelect, choices=CHOICES, required=False)
    poll_other = forms.CharField(max_length=500, min_length=2,
                                   label=_('Where did you hear about as'),
                                   required=False,
                                   help_text=_('Other, where?'))

    public_memberlist = forms.BooleanField(
        label=_('My name (first and last name) and homepage can be shown in the public memberlist'), required=False)


class PersonMembershipForm(PersonMembershipInfoForm):
    email_forward = forms.CharField(min_length=2)


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
    organization_registration_number = OrganizationRegistrationNumber(
                                 label=_('Business ID'),
                                 required=True,
                                 help_text=_('Business ID given by Patentti- ja rekisterihallitus'))
    extra_info = forms.CharField(label=_('Additional information'),
                                 widget=forms.Textarea(attrs={'cols': '40'}),
                                 required=False,
                                 help_text=_('You can write additional questions or details here'),
                                 max_length=1000)
    public_memberlist = forms.BooleanField(
        label=_('Organization information (name and homepage) can be shown in the public memberlist'), required=False)


class BaseContactForm(forms.Form):
    street_address = forms.CharField(max_length=30, min_length=4,
                                     error_messages={'required': _('Street address required.')},
                                     label=_('Street address'))
    postal_code = forms.RegexField(regex='^[a-z0-9-]{2,10}$',
                                   error_messages={'required': _('Postal code required.')},
                                   label=_('Postal code'))
    post_office = forms.CharField(max_length=30, min_length=2, label=_('Post office'))
    country = forms.CharField(max_length=128, label=_('Country'), initial=_('Finland'))
    phone = PhoneNumberField(error_messages={'invalid': _('Phone invalid.')},
                             label=_('Phone number'),
                             help_text=_('Phone number that accepts calls'))
    sms = PhoneNumberField(error_messages={'invalid': _('SMS number invalid.')},
                           label=_('SMS number'),
                           help_text=_('Phone number that accepts text messages. Used for sending the password.'))
    email = forms.EmailField(label=_('E-mail'))
    homepage = forms.URLField(required=False,
                              label=_('Homepage'),
                              help_text=_('Homepage for the public member list'))

    def clean(self):
        if 'postal_code' in self.cleaned_data and (self.cleaned_data['country'] == 'Finland' or
                                                         self.cleaned_data['country'] == 'Suomi'):
            if re.match(r"^[\d]{5}$", self.cleaned_data['postal_code']) is None:
                self._errors["postal_code"] = self.error_class(
                    [_("Postal codes in Finland must consist of 5 numbers.")])
                del self.cleaned_data["postal_code"]
        return self.cleaned_data


class PersonBaseContactForm(forms.Form):
    first_name = forms.CharField(max_length=40, min_length=1,
                                 error_messages={'required': _('First name required.')},
                                 label=_('First name'))
    given_names = forms.CharField(max_length=30, min_length=2,
                                  error_messages={'required': _('Given names required.')},
                                  label=_('Given names'),
                                  help_text=_('Including first name'))
    last_name = forms.CharField(max_length=30, min_length=2,
                                error_messages={'required': _('Last name required.')},
                                label=_('Last name'))


class ContactForm(forms.ModelForm):
    """Contact editing form for authenticated users"""

    class Meta:
        model = Contact
        fields = '__all__'


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


class SupportingPersonApplicationForm(PersonContactForm, PersonMembershipInfoForm):
    pass
