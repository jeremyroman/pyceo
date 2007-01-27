# $Id: terms.py 44 2006-12-31 07:09:27Z mspang $
"""
Terms Routines

This module contains functions for manipulating
terms, such as determining the current term,
finding the next or previous term, converting
dates to terms, and more.
"""
import time, datetime, re

# year to count terms from
EPOCH = 1970

# seasons list
SEASONS = [ 'w', 's', 'f' ]


def valid(term):
    """
    Determines whether a term is well-formed:

    Parameters:
        term - the term string

    Returns: whether the term is valid (boolean)

    Example: valid("f2006") -> True
    """

    regex = '^[wsf][0-9]{4}$'
    return re.match(regex, term) != None


def parse(term):
    """Helper function to convert a term string to the number of terms
       since the epoch. Such numbers are intended for internal use only."""

    if not valid(term):
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
        SPRING = MAY TO AUGUST
        FALL   = SEPTEMBER TO DECEMBER
    
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

    assert parse('f2006') == 110
    assert generate(110) == 'f2006'
    assert next('f2006') == 'w2007'
    assert previous('f2006') == 's2006'
    assert delta('f2006', 'w2007') == 1
    assert add('f2006', delta('f2006', 'w2010')) == 'w2010'
    assert interval('f2006', 3) == ['f2006', 'w2007', 's2007']
    assert from_timestamp(1166135779) == 'f2006'
    assert parse( current() ) >= 110
    assert next_unregistered( [current()] ) == next( current() )
    assert next_unregistered( [] ) == current()
    assert next_unregistered( [previous(current())] ) == current()
    assert next_unregistered( [add(current(), -2)] ) == current()

    print "All tests passed." "\n"
