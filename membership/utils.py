# -*- coding: utf-8 -*-

from datetime import datetime

from django_comments.models import Comment
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldError
from django.utils.encoding import force_unicode
from django.utils.translation import ugettext_lazy as _
from django.utils.html import escape
from django.db.models import Sum

# http://code.activestate.com/recipes/576644/

def dict_diff(first, second):
    """ Return a dict of keys that differ with another config object.  If a value is
        not found in one fo the configs, it will be represented by KEYNOTFOUND.
        @param first:   Fist dictionary to diff.
        @param second:  Second dicationary to diff.
        @return diff:   Dict of Key => (first.val, second.val)
    """
    diff = {}
    sd1 = set(first)
    sd2 = set(second)
    #Keys missing in the second dict
    for key in sd1.difference(sd2):
        diff[key] = (first[key], None)
    #Keys missing in the first dict
    for key in sd2.difference(sd1):
        diff[key] = (None, second[key])
    #Check for differences
    for key in sd1.intersection(sd2):
        if first[key] != second[key]:
            diff[key] = (first[key], second[key])
    return diff

def diff_humanize(diff):
    # Human readable output
    txt = ""
    for key in diff:
        if key == 'last_changed' or key.startswith("_"):
            continue
        change = list(diff[key])
        try:
            change[0] = change[0].strftime("%Y-%m-%d %H:%M")
        except: pass
        try:
            change[1] = change[1].strftime("%Y-%m-%d %H:%M")
        except: pass
        if change[0] == None:
            txt += "%s: () -> '%s'. " % (key, change[1])
        elif change[1] == None:
            txt += "%s: '%s' -> (). " % (key, change[0])
        else:
            txt += "%s: '%s' => '%s'. " % (key, change[0], change[1])
    return txt

def log_change(object, user, before=None, after=None, change_message=None):
    if not change_message:
        if before and after:
            change_message  = diff_humanize(dict_diff(before, after))
        else:
            change_message = "Some changes were made"
    if not change_message:
        return
    from django.contrib.admin.models import LogEntry, CHANGE
    LogEntry.objects.log_action(
        user_id         = user.pk,
        content_type_id = ContentType.objects.get_for_model(object).pk,
        object_id       = object.pk,
        object_repr     = force_unicode(object),
        action_flag     = CHANGE,
        change_message  = change_message
    )

def change_message_to_list(row):
    """Convert humanized diffs to a list for usage in template"""
    retval = []
    for message in row.change_message.strip().strip(".").split(". "):
        if ":" not in message:
            continue
        if "->" not in message and "=>" not in message:
            continue

        key, value  = message.split(":",1)
        key = key.strip().strip("'")
        if "=>" in value:
            old,new = value.split("=>",1)
        elif "->" in value:
            old, new = value.split("->",1)
        else:
            continue
        old = old.strip().strip("'")
        new = new.strip().strip("'")
        retval.append([key, old, new])
    return retval

def bake_log_entries(raw_log_entries):
    ACTION_FLAGS = {1 : _('Addition'),
                    2 : _('Change'),
                    3 : _('Deletion')}
    for x in raw_log_entries:
        x.action_flag_str = unicode(ACTION_FLAGS[x.action_flag])
        x.change_list = change_message_to_list(x)
    return raw_log_entries

def serializable_membership_info(membership):
    """
    A naive method of dict construction is used here. It's not very fancy,
    but Django's serialization seems to take such a tedious route that this
    seems simpler.
    """
    from services.models import valid_aliases, Service
    json_obj = {}
    # Membership details
    for attr in ['type', 'status', 'created', 'last_changed', 'municipality',
                 'nationality', 'public_memberlist', 'extra_info', 'birth_year',
                 'organization_registration_number']:
        # Get the translated value for choice fields, not database field values
        if attr in ['type', 'status']:
            attr_val = getattr(membership, 'get_' + attr + '_display')()
        else:
            attr_val = escape(getattr(membership, attr, u''))
        if isinstance(attr_val, basestring):
            json_obj[attr] = attr_val
        elif isinstance(attr_val, datetime):
            json_obj[attr] = attr_val.ctime()
        else:
            json_obj[attr] = unicode(attr_val)

    # Contacts
    contacts_json_obj = {}
    json_obj['contacts'] = contacts_json_obj
    for attr in ['person', 'billing_contact', 'tech_contact', 'organization']:
        attr_val = getattr(membership, attr, None)
        if not attr_val:
            continue

        contact_json_obj = {}
        for c_attr in ['first_name', 'given_names', 'last_name',
                       'organization_name', 'street_address', 'postal_code',
                       'post_office', 'country', 'phone', 'sms', 'email',
                       'homepage']:
            c_attr_val = escape(getattr(attr_val, c_attr, u''))
            contact_json_obj[c_attr] = c_attr_val
            contacts_json_obj[attr] = contact_json_obj

    # Events (comments + log entries)
    comment_list = []
    log_entry_list = []
    event_list = []
    json_obj['comments'] = comment_list
    json_obj['log_entries'] = log_entry_list
    json_obj['events'] = event_list

    # Aliases
    json_obj['aliases'] = ", ".join((escape(alias.name) for alias in valid_aliases(membership)))

    json_obj['services'] = ", ".join((escape(str(service))
                                      for service in Service.objects.filter(owner=membership)))

    # FIXME: This is broken. Should probably replace:
    # {% get_comment_list for [object] as [varname] %}
    # http://docs.djangoproject.com/en/1.2/ref/contrib/comments/
    comments = Comment.objects.filter(object_pk=membership.pk)
    for comment in comments:
        d = { 'user_name': unicode(comment.user),
              'text': escape(comment.comment),
              'date': comment.submit_date }
        comment_list.append(d)
        event_list.append(d)

    log_entries = bake_log_entries(membership.logs.all())
    for entry in log_entries:
        d = { 'user_name': unicode(entry.user),
              'text': "%s %s" % (escape(unicode(entry.action_flag_str)), escape(unicode(entry.change_message))),
              'date': entry.action_time }
        log_entry_list.append(d)
        event_list.append(d)

    def cmp_fun(x, y):
        if x['date'] > y['date']:
            return 1
        if x['date'] == y['date']:
            return 0
        return -1

    comment_list.sort(cmp_fun)
    log_entry_list.sort(cmp_fun)
    event_list.sort(cmp_fun)

    def ctimeify(lst):
        for item in lst:
            if isinstance(item['date'], basestring):
                continue # some are already in ctime format since they are part of multiple lists
            item['date'] = item['date'].ctime()
    ctimeify(comment_list)
    ctimeify(log_entry_list)
    ctimeify(event_list)

    return json_obj



def admtool_membership_details(membership):
    from services.models import valid_aliases, Service
    json_obj = {}
    # Membership details
    for attr in ['id', 'type', 'status', 'created', 'last_changed', 'municipality',
                 'nationality', 'public_memberlist', 'extra_info', 'birth_year',
                 'organization_registration_number']:
        # Get the translated value for choice fields, not database field values
        attr_val = escape(getattr(membership, attr, u''))
        if isinstance(attr_val, basestring):
            json_obj[attr] = attr_val
        elif isinstance(attr_val, datetime):
            json_obj[attr] = attr_val.ctime()
        else:
            json_obj[attr] = unicode(attr_val)

    # Contacts
    contacts_json_obj = {}
    json_obj['contacts'] = contacts_json_obj
    for attr in ['person', 'billing_contact', 'tech_contact', 'organization']:
        attr_val = getattr(membership, attr, None)
        if not attr_val:
            continue

        contact_json_obj = {}
        for c_attr in ['first_name', 'given_names', 'last_name',
                       'organization_name', 'street_address', 'postal_code',
                       'post_office', 'country', 'phone', 'sms', 'email',
                       'homepage']:
            c_attr_val = escape(getattr(attr_val, c_attr, u''))
            contact_json_obj[c_attr] = c_attr_val
            contacts_json_obj[attr] = contact_json_obj

    # Events (comments + log entries)
    comment_list = []
    log_entry_list = []
    event_list = []
    json_obj['comments'] = comment_list
    json_obj['log_entries'] = log_entry_list
    json_obj['events'] = event_list

    # Aliases
    json_obj['aliases'] = [unicode(alias) for alias in valid_aliases(membership)]

#    json_obj['services'] = ", ".join((escape(str(service))
#                                      for service in Service.objects.filter(owner=membership)))
    json_obj['services'] = services_json_obj = []
    for service in Service.objects.filter(owner=membership):
        service_obj = {}
        service_obj['type'] = escape(unicode(service.servicetype))
        if service.alias:
            service_obj['alias'] = escape(unicode(service.alias))
        if service.data:
            service_obj['data'] = escape(unicode(service.data))
        services_json_obj.append(service_obj)

    # FIXME: This is broken. Should probably replace:
    # {% get_comment_list for [object] as [varname] %}
    # http://docs.djangoproject.com/en/1.2/ref/contrib/comments/
    comments = Comment.objects.filter(object_pk=membership.pk)
    for comment in comments:
        d = { 'user_name': unicode(comment.user),
              'text': escape(comment.comment),
              'date': comment.submit_date }
        comment_list.append(d)
        event_list.append(d)

    log_entries = bake_log_entries(membership.logs.all())
    for entry in log_entries:
        d = { 'user_name': unicode(entry.user),
              'text': "%s %s" % (escape(unicode(entry.action_flag_str)), escape(unicode(entry.change_message))),
              'date': entry.action_time }
        log_entry_list.append(d)
        event_list.append(d)

    def cmp_fun(x, y):
        if x['date'] > y['date']:
            return 1
        if x['date'] == y['date']:
            return 0
        return -1

    comment_list.sort(cmp_fun)
    log_entry_list.sort(cmp_fun)
    event_list.sort(cmp_fun)

    def ctimeify(lst):
        for item in lst:
            if isinstance(item['date'], basestring):
                continue # some are already in ctime format since they are part of multiple lists
            item['date'] = item['date'].ctime()
    ctimeify(comment_list)
    ctimeify(log_entry_list)
    ctimeify(event_list)

    return json_obj
def tupletuple_to_dict(tupletuple):
    '''Convert a tuple of tuples to dict

    >>> tupletuple = (('A', 'Value1'), ('B', 'Value2'))
    >>> d = tupletuple_to_dict(tupletuple)
    >>> d['A']
    'Value1'
    >>> d['B']
    'Value2'
    '''
    d = {}
    for t in tupletuple:
        (key, value) = t
        d[key] = value
    return d


def group_iban(string):
    """
    Split IBAN to have space after every fourth character.
    e.g. 1111 1111 1111 1111 11
    :param string: input string
    :return: modified string
    """
    string = ''.join(string.split())
    return ''.join(e if (i+1) % 4 else e+" " for (i,e) in enumerate(string)).strip()


def group_reference(string):
    """
    Group reference number to have space after every fifth number
    e.g. 1 23456
    :param string: input string
    :return: modified string
    """
    string = ''.join(string.split())
    return ''.join(e if (len(string) - i - 1) % 5 else e + " " for (i, e) in enumerate(string)).strip()