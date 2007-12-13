"""
Common Test Routines

This module contains helpful functions called by each module's test suite.
"""
from types import FunctionType, MethodType, ClassType, TypeType


class TestException(Exception):
    """Exception class for test failures."""


def test(subject):
    """Print a test message."""
    if type(subject) in (MethodType, FunctionType, ClassType, TypeType):
        print "testing %s()..." % subject.__name__,
    else:
        print "testing %s..." % subject,


def success():
    """Print a success message."""
    print "pass."


def assert_equal(expected, actual):
    if expected != actual:
        message = "Expected (%s)\nWas      (%s)" % (repr(expected), repr(actual))
        fail(message)


def fail(message):
    print "failed!"
    raise TestException("Test failed:\n%s" % message)


def negative(call, args, excep, message):
    try:
        call(*args)
        fail(message)
    except excep:
        pass
