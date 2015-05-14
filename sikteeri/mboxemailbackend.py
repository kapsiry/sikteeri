from __future__ import with_statement

from contextlib import contextmanager
from fcntl import flock, LOCK_EX, LOCK_UN

import email.utils

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


@contextmanager
def file_lock(file_handle):
    """Lock function for with-statement.

    See http://bugs.python.org/issue6194 to find out why
    http://docs.python.org/library/os.html#os.O_SHLOCK cannot be used.
    """
    return_value = flock(file_handle, LOCK_EX)

    try:
        yield return_value
    finally:
        flock(file_handle, LOCK_UN)


class EmailBackend(BaseEmailBackend):

    def __init__(self, *args, **kwargs):
        self.file_path = getattr(settings, 'EMAIL_MBOX_FILE_PATH', None)
        with open(self.file_path, 'a') as f:
            with file_lock(f):
                f.write('')
        super(EmailBackend, self).__init__(*args, **kwargs)

    def send_messages(self, email_messages):
        if not email_messages:
            return
        try:
            with open(self.file_path, 'a') as f:
                with file_lock(f):
                    for message in email_messages:
                        f.write("From sikteeri Mon Mar 23 08:36:59 2009\n")
                        f.write(message.message().as_string())
                        f.write('\n\n')
        except:
            if not self.fail_silently:
                raise
        return len(email_messages)
