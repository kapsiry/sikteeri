#!/usr/bin/env python
# -*- coding: utf-8 -*-
# import cgitb
# cgitb.enable()

import os
import sys
import logging
import traceback

from os import environ as env
from commands import getstatusoutput as gso
from contextlib import contextmanager

gunicorn_pid = os.path.join(os.environ['HOME'], 'gunicorn.pid')

@contextmanager
def working_directory(dst_dir):
    current_dir = os.getcwd()
    os.chdir(dst_dir)
    try:
        yield dst_dir
    finally:
        os.chdir(current_dir)


os.umask(0o77)

with working_directory('../'):
    logger = logging.getLogger('')
    logger.setLevel(logging.DEBUG)

    handler = logging.FileHandler('cgi-log')
    handler.setLevel(logging.INFO)

    formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(name)-16s %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    try:
        # Revert possible changes on version file
        gso('git checkout sikteeri/version.py')

        s, o = gso('git pull')
        if s != 0:
            raise Exception("git pull returned %(s)s (%(o)s)" % vars())

        # Compile translations
        s, o = gso('source ../env/bin/activate && ./build.sh')

        pidfile = gunicorn_pid
        pid = None
        if not os.path.exists(pidfile):
            raise Exception("pidfile %s does not exist" % pidfile)
        with open(pidfile) as f:
            pid = int(f.read())
            os.kill(pid, 1)

        # Write version number
        s, o = gso('git describe')
        if s == 0:
            with open('sikteeri/version.py', 'a') as f:
                f.write('''VERSION = "%s"\n''' % o)

        print "Content-Type: text/plain"
        print
        print 'OK'
        logger.info('Successfully updated')
    except Exception, e:
        logging.getLogger('deploy.cgi').critical(traceback.format_exc(e))
