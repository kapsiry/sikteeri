# -*- coding: utf-8 -*-

import re
import json
import logging
logger = logging.getLogger("services.views")
from membership.utils import log_change
from membership.utils import bake_log_entries
from membership.models import Membership
from membership.forms import VALID_USERNAME_RE
from services.models import Alias
from django.contrib.auth.decorators import permission_required
from django.contrib import messages
from django.forms import ModelForm, ModelChoiceField
from django.forms.models import model_to_dict
from django.http import HttpResponse
from django.shortcuts import render_to_response, get_object_or_404, redirect
from django.template import RequestContext
from django.utils.translation import ugettext_lazy as _

@permission_required('services.manage_aliases')
def alias_edit(request, id, template_name='membership/entity_edit.html'):
    alias = get_object_or_404(Alias, id=id)

    class Form(ModelForm):
        class Meta:
            model = Alias
            fields = '__all__'

        owner = ModelChoiceField(queryset=Membership.objects.filter(pk=alias.owner.id),
                                 empty_label=None)

        @staticmethod
        def clean_name():
            return alias.name

        @staticmethod
        def clean_owner():
            return alias.owner

        def disable_fields(self):
            self.fields['name'].required = False
            self.fields['name'].widget.attrs['readonly'] = 'readonly'
            self.fields['owner'].required = False
            self.fields['owner'].widget.attrs['readonly'] = 'readonly'

    if request.method == 'POST':
        form = Form(request.POST, instance=alias)
        before = model_to_dict(alias)
        form.disable_fields()
        if form.is_valid():
            form.save()
            after = model_to_dict(alias)
            log_change(alias, request.user, before, after)
            return redirect('alias_edit', id) # form stays as POST otherwise if someone refreshes
    else:
        form = Form(instance=alias)
        form.disable_fields()
    logentries = bake_log_entries(alias.logs.all())
    return render_to_response(template_name, {'form': form,
        'alias': alias, 'logentries': logentries},
        context_instance=RequestContext(request))


@permission_required('services.manage_aliases')
def alias_add_for_member(request, id, template_name='membership/membership_add_alias.html'):
    membership = get_object_or_404(Membership, id=id)

    class Form(ModelForm):
        class Meta:
            model = Alias
            exclude = ('owner', 'account', 'expiration_date')

    if request.method == 'POST':
        form = Form(request.POST)
        if form.is_valid():
            f = form.cleaned_data
            name = f['name']
            comment = f['comment']
            alias = Alias(owner=membership, name=name, comment=comment)
            alias.save()
            messages.success(request,
                _('Alias {alias} successfully created for {membership}.'
                  '').format(alias=alias, membership=membership))
            logger.info("Alias %s added by %s." % (alias, request.user.username))
            return redirect('membership_edit', membership.id)
    else:
        form = Form()

    return render_to_response(template_name,
                              {'form': form,
                               'membership': membership },
                              context_instance=RequestContext(request))


# FIXME: Here should probably be rate limiting, but it isn't simple.
# Would this suffice? <http://djangosnippets.org/snippets/2276/>
# This is called from membership.views.handle_json!
def check_alias_availability(request, alias):
    if Alias.objects.filter(name__iexact=alias).count() == 0:
        return HttpResponse("true", content_type='text/plain')
    return HttpResponse("false", content_type='text/plain')

# This is called from membership.views.handle_json!
# Public access
def validate_alias(request, alias):
    exists = True
    valid = True
    if Alias.objects.filter(name__iexact=alias).count() == 0:
        exists = False
    if re.match(VALID_USERNAME_RE, alias) == None:
        valid = False
    json_obj = {'exists' : exists, 'valid' : valid}
    return HttpResponse(json.dumps(json_obj, sort_keys=True, indent=4),
                        content_type='application/json')
