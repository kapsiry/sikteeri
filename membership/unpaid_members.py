# -*- coding: utf-8 -*-
from django.db.models import Q

from .models import BillingCycle, STATUS_APPROVED, STATUS_DISASSOCIATED


def unpaid_members_data():
    unpaid_members = []
    unpaid_reminders = BillingCycle.objects.filter(bill__reminder_count=2, membership__status='A', is_paid=False)
    for bc in unpaid_reminders:
        member = bc.membership
        accounts = member.alias_set.filter(account=True)
        for account in accounts:
            value = (member.id, account.name)
            if value not in unpaid_members:
                unpaid_members.append(value)
    return unpaid_members


def members_to_lock():
    users = []

    case_approved_but_unpaid = Q(membership__status=STATUS_APPROVED) & Q(bill__reminder_count=2) & Q(is_paid=False)
    case_diassociated = Q(membership__status=STATUS_DISASSOCIATED)

    unpaid_reminders = BillingCycle.objects.filter(case_approved_but_unpaid | case_diassociated)
    for bc in unpaid_reminders:
        member = bc.membership
        accounts = member.alias_set.filter(account=True)
        for account in accounts:
            value = (member.id, account.name)
            if value not in users:
                users.append(value)
    return users