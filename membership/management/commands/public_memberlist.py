# -*- encoding: utf-8 -*-

from django.db.models import Q
from django.core.management.base import NoArgsCommand
from django.template.loader import render_to_string
from django.conf import settings

from membership.models import *

class Command(NoArgsCommand):
    def handle_noargs(self, **options):
        mship = Membership.objects.filter(status__exact='A')
        count = mship.count()
        mship = mship.filter(public_memberlist__exact="True")
        mship = mship.order_by("person__last_name", "person__first_name")
        person_q = Q(person_set__in=mship)
        person_contacts = Contact.objects.filter(person_q)
        return render_to_string('membership/public_memberlist.xml', {
                                  'count': count,
		                          'member_list': person_contacts
                               } ).encode('utf-8')
