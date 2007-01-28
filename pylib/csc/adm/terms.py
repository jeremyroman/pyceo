"""
Terms Routines

This module contains functions for manipulating terms, such as determining
the current term, finding the next or previous term, converting dates to
terms, and more.
"""
import time, datetime, re

# year to count terms from
EPOCH = 1970

# seasons list
SEASONS = [ 'w', 's', 'f' ]


def validate(term):
    """
    Determines whether a term is well-formed.

    Parameters:
        term - the term string

    Returns: whether the term is valid (boolean)

    Example: validate("f2006") -> True
    """

    regex = '^[wsf][0-9]{4}$'
    return re.match(regex, term) is not None


def parse(term):
    """Helper function to convert a term string to the number of terms
       since the epoch. Such numbers are intended for internal use only."""

    if not validate(term):
        raise Exception("malformed term: %s" % term)

    year = int( term[1:] )
    season = SEASONS.index( term[0] )

    return (year - EPOCH) * len(SEASONS) + season


def generate(term):
    """Helper function to convert a year and season to a term string."""
    
    year = int(term / len(SEASONS)) + EPOCH
    season = term % len(SEASONS)
    
    return "%s%04d" % ( SEASONS[season], year )


def next(term):
    """
    Returns the next term. (convenience function)

    Parameters:
        term - the term string

    Retuns: the term string of the following term

    Example: next("f2006") -> "w2007"
    """
    
    return add(term, 1)


def previous(term):
    """
    Returns the previous term. (convenience function)

    Parameters:
        term - the term string

    Returns: the term string of the preceding term

    Example: previous("f2006") -> "s2006"
    """

    return add(term, -1)


def add(term, offset):
    """
    Calculates a term relative to some base term.
    
    Parameters:
        term   - the base term
        offset - the number of terms since term (may be negative)

    Returns: the term that comes offset terms after term
    """

    return generate(parse(term) + offset)


def delta(initial, final):
    """
    Calculates the distance between two terms.
    It should be true that add(a, delta(a, b)) == b.

    Parameters:
        initial - the base term
        final   - the term at some offset from the base term

    Returns: the offset of final relative to initial
    """

    return parse(final) - parse(initial)


def compare(first, second):
    """
    Compares two terms. This function is suitable
    for use with list.sort().

    Parameters:
        first  - base term for comparison
        second - term to compare to

    Returns: > 0 (if first >  second)
             = 0 (if first == second)
             < 0 (if first <  second)
    """
    return delta(second, first)
             

def interval(base, count):
    """
    Returns a list of adjacent terms.

    Parameters:
        base    - the first term in the interval
        count   - the number of terms to include

    Returns: a list of count terms starting with initial

    Example: interval('f2006', 3) -> [ 'f2006', 'w2007', 's2007' ]
    """
    
    terms = []

    for num in xrange(count):
        terms.append( add(base, num) )
    
    return terms
        

def tstamp(timestamp):
    """Helper to convert seconds since the epoch
    to terms since the epoch."""

    # let python determine the month and year
    date = datetime.date.fromtimestamp(timestamp)

    # determine season
    if date.month <= 4:
        season = SEASONS.index('w')
    elif date.month <= 8:
        season = SEASONS.index('s')
    else:
        season = SEASONS.index('f')

    return (date.year - EPOCH) * len(SEASONS) + season


def from_timestamp(timestamp):
    """
    Converts a number of seconds since
    the epoch to a number of terms since
    the epoch.

    This function notes that:
        WINTER = JANUARY to APRIL
        SPRING = MAY to AUGUST
        FALL   = SEPTEMBER to DECEMBER
    
    Parameters:
        timestamp - number of seconds since the epoch

    Returns: the number of terms since the epoch

    Example: from_timestamp(1166135779) -> 'f2006'
    """

    return generate( tstamp(timestamp) )
    

def curr():
    """Helper to determine the current term."""

    return tstamp( time.time() )


def current():
    """
    Determines the current term.

    Returns: current term

    Example: current() -> 'f2006'
    """

    return generate( curr() )
    

def next_unregistered(registered):
    """
    Find the first future or current unregistered term.
    Intended as the 'default' for registrations.

    Parameters:
        registered - a list of terms a member is registered for

    Returns: the next unregistered term
    """
    
    # get current term number
    now = curr()

    # never registered -> current term is next
    if len( registered) < 1:
        return generate( now )

    # return the first unregistered, or the current term (whichever is greater)
    return generate(max([max(map(parse, registered))+1, now]))



### Tests ###

if __name__ == '__main__':

    from csc.common.test import *

    test(parse); assert_equal(110, parse('f2006')); success()
    test(generate); assert_equal('f2006', generate(110)); success()
    test(next); assert_equal('w2007', next('f2006')); success()
    test(previous); assert_equal('s2006', previous('f2006')); success()
    test(delta); assert_equal(1, delta('f2006', 'w2007')); success()
    test(compare); assert_equal(-1, compare('f2006', 'w2007')); success()
    test(add); assert_equal('w2010', add('f2006', delta('f2006', 'w2010'))); success()
    test(interval); assert_equal(['f2006', 'w2007', 's2007'], interval('f2006', 3)); success()
    test(from_timestamp); assert_equal('f2006', from_timestamp(1166135779)); success()
    test(current); assert_equal(True, parse( current() ) >= 110 ); success()

    test(next_unregistered)
    assert_equal( next(current()), next_unregistered([ current() ]))
    assert_equal( current(), next_unregistered([]))
    assert_equal( current(), next_unregistered([ previous(current()) ]))
    assert_equal( current(), next_unregistered([ add(current(), -2) ]))
    success()
