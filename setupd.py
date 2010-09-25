#!/usr/bin/env python

from distutils.core import setup

setup(
    name='ceod',
    description='CSC Electronic Office Daemon',
    scripts=['src/op-mysql','src/op-mailman'],
)

