from __future__ import with_statement

import sys
import threading

from datetime import datetime

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

class EmailBackend(BaseEmailBackend):
    def __init__(self, *args, **kwargs):
        self._lock = threading.RLock()
        self.file_path = getattr(settings, 'EMAIL_MBOX_FILE_PATH', None)
        with open(self.file_path, 'a') as f:
            f.write('')
        super(EmailBackend, self).__init__(*args, **kwargs)

    def send_messages(self, email_messages):
        if not email_messages:
            return
        self._lock.acquire()
        try:
            # The try-except is nested to allow for
            # Python 2.4 support (Refs #12147)
            try:
                with open(self.file_path, 'a') as f:                
                    for message in email_messages:
                        f.write("From sikteeri %s\n" % datetime.now().strftime("%a %b %d %H:%M:%S EET %Y"))
                        f.write(message.message().as_string())
                        f.write('\n\n')
            except:
                if not self.fail_silently:
                    raise
        finally:
            self._lock.release()
        return len(email_messages)
