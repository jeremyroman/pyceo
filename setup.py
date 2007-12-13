#!/usr/bin/env python

from distutils.core import setup

setup(
    name='ceo',
    description='CSC Electronic Office',
    packages=[ 'ceo', 'ceo.urwid' ],
    scripts=['bin/ceo', 'bin/ceoquery', 'bin/csc-chfn', 'bin/csc-chsh'],
)

