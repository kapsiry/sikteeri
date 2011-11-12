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
        s, o = gso('git pull')
        if s != 0:
            raise Exception("git pull returned %(s)s (%(o)s)" % vars())

        s, o = gso('touch webroot/django.wsgi')
        if s != 0:
            raise Exception("touch returned %(s)s (%(o)s)" % vars())

        print "Content-Type: text/plain"
        print
        print 'OK'
    except Exception, e:
        logging.getLogger('deploy.cgi').critical(traceback.format_exc(e))
