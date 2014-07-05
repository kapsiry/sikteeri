#!/usr/bin/env python

from django.utils.crypto import get_random_string

# https://github.com/django/django/blob/master/django/core/management/commands/startproject.py
def generate_secret_key():
    # Create a random SECRET_KEY to put it in the main settings.
    chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
    return get_random_string(50, chars)


def main():
    key = generate_secret_key()
    print('SECRET_KEY = \'{}\''.format(key))

if __name__ == '__main__':
    main()
