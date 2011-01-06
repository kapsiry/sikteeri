#!/usr/bin/env python
# encoding: utf-8

# This file contains the utility functions that can be used from models.
# It cannot import from the models for that reason.

import sys
import os

def tupletuple_to_dict(tupletuple):
    '''Convert a tuple of tuples to dict

    >>> tupletuple = (('A', 'Value1'), ('B', 'Value2'))
    >>> d = tupletuple_to_dict(tupletuple)
    >>> d['A']
    'Value1'
    >>> d['B']
    'Value2'
    '''
    d = {}
    for t in tupletuple:
        (key, value) = t
        d[key] = value
    return d

def main():
    import doctest
    doctest.testmod()

if __name__ == '__main__':
    main()

