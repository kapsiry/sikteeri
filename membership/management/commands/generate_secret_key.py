from django.core.management.base import NoArgsCommand, CommandError
from django.utils.crypto import get_random_string

# https://github.com/django/django/blob/master/django/core/management/commands/startproject.py
def generate_secret_key():
    # Create a random SECRET_KEY to put it in the main settings.
    chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
    return get_random_string(50, chars)

class Command(NoArgsCommand):
    help = 'Generate a secret key for Django settings'

    def handle_noargs(self, **options):
        key = generate_secret_key()
        self.stdout.write('SECRET_KEY = \'{}\''.format(key))
