#!/usr/bin/env python

from distutils.core import setup

setup(
    name='ceo',
    description='CSC Electronic Office',
    packages=[ 'csc', 'csc.common', 'csc.adm', 'csc.backends', 'csc.apps', 'csc.apps.urwid' ],
    package_dir = {'': 'pylib'},
    scripts=['bin/ceo', 'bin/ceoquery', 'bin/csc-chfn', 'bin/csc-chsh'],
)

