"""
Exceptions Module

This module provides some simple but generally useful exception classes.
"""

class InvalidArgument(Exception):
    """Exception class for bad argument values."""
    def __init__(self, argname, argval, explanation):
        self.argname, self.argval, self.explanation = argname, argval, explanation
    def __str__(self):
        return 'Bad argument value "%s" for %s: %s' % (self.argval, self.argname, self.explanation)
