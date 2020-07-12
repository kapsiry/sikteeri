# -*- encoding: utf-8 -*-

from django.core.management.base import BaseCommand
from django.template.loader import render_to_string

from membership.public_memberlist import public_memberlist_data


class Command(BaseCommand):
    def handle(self, *args, **options):
        template_name = 'membership/public_memberlist.xml'
        data = public_memberlist_data()
        return render_to_string(template_name, data)
