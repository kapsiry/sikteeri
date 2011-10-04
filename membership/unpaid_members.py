# -*- coding: utf-8 -*-

from models import BillingCycle

def unpaid_members_data():
    unpaid_members = []
    unpaid_reminders = BillingCycle.objects.filter(bill__reminder_count=2, membership__status='A', is_paid=False)
    for bc in unpaid_reminders:
        member = bc.membership
        accounts = member.alias_set.filter(account=True)
        for account in accounts:
            unpaid_members.append((member.id, account.name))
    return unpaid_members
