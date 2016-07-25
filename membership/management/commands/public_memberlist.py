from django.db.models import Q
from django.core.management.base import NoArgsCommand
from django.template.loader import render_to_string
from django.conf import settings

from membership.models import *
from membership.public_memberlist import public_memberlist_data

class Command(NoArgsCommand):
    def handle_noargs(self, **options):
        template_name = 'membership/public_memberlist.xml'
        data = public_memberlist_data()
        return render_to_string(template_name, data)
