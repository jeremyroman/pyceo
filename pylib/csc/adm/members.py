# $Id: members.py 44 2006-12-31 07:09:27Z mspang $
"""
CSC Member Management

This module contains functions for registering new members, registering
members for terms, searching for members, and other member-related
functions.

Transactions are used in each method that modifies the database. 
Future changes to the members database that need to be atomic
must also be moved into this module.
"""

import re
from csc.adm import terms
from csc.backends import db
from csc.common.conf import read_config




### Configuration

CONFIG_FILE = '/etc/csc/members.cf'

cfg = {}


def load_configuration():
    """Load Members Configuration"""

    # configuration already loaded?
    if len(cfg) > 0:
        return

    # read in the file
    cfg_tmp = read_config(CONFIG_FILE)

    if not cfg_tmp:
        raise MemberException("unable to read configuration file: %s"
                % CONFIG_FILE)

    # check that essential fields are completed
    mandatory_fields = [ 'server', 'database', 'user', 'password' ]

    for field in mandatory_fields:
        if not field in cfg_tmp:
            raise MemberException("missing configuratino option: %s" % field)
        if not cfg_tmp[field]:
            raise MemberException("null configuration option: %s" %field)

    # update the current configuration with the loaded values
    cfg.update(cfg_tmp)



### Exceptions ###

class MemberException(Exception):
    """Exception class for member-related errors."""

class DuplicateStudentID(MemberException):
    """Exception class for student ID conflicts."""
    pass

class InvalidStudentID(MemberException):
    """Exception class for malformed student IDs."""
    pass

class InvalidTerm(MemberException):
    """Exception class for malformed terms."""
    pass

class NoSuchMember(MemberException):
    """Exception class for nonexistent members."""
    pass



### Connection Management ###

# global database connection
connection = db.DBConnection()


def connect():
    """Connect to PostgreSQL."""
    
    load_configuration()
    
    connection.connect(cfg['server'], cfg['database'])
       

def disconnect():
    """Disconnect from PostgreSQL."""
    
    connection.disconnect()


def connected():
    """Determine whether the connection has been established."""

    return connection.connected()


### Member Table ###

def new(realname, studentid=None, program=None):
    """
    Registers a new CSC member. The member is added
    to the members table and registered for the current
    term.

    Parameters:
        realname  - the full real name of the member
        studentid - the student id number of the member
        program   - the program of study of the member

    Returns: the memberid of the new member

    Exceptions:
        DuplicateStudentID - if the student id already exists in the database
        InvalidStudentID   - if the student id is malformed

    Example: new("Michael Spang", program="CS") -> 3349
    """

    # blank attributes should be NULL
    if studentid == '': studentid = None
    if program == '': program = None

    # check the student id format
    regex = '^[0-9]{8}$'
    if studentid != None and not re.match(regex, str(studentid)):
        raise InvalidStudentID("student id is invalid: %s" % studentid)

    # check for duplicate student id
    member = connection.select_member_by_studentid(studentid)
    if member:
        raise DuplicateStudentID("student id exists in database: %s" % studentid)

    # add the member
    memberid = connection.insert_member(realname, studentid, program)

    # register them for this term
    connection.insert_term(memberid, terms.current())

    # commit the transaction
    connection.commit()

    return memberid


def get(memberid):
    """
    Look up attributes of a member by memberid.

    Parameters:
        memberid - the member id number

    Returns: a dictionary of attributes

    Example: get(3349) -> {
                 'memberid': 3349,
                 'name': 'Michael Spang',
                 'program': 'Computer Science',
                 ...
             }
    """

    return connection.select_member_by_id(memberid)


def get_userid(userid):
    """
    Look up attributes of a member by userid.

    Parameters:
        userid - the UNIX user id

    Returns: a dictionary of attributes

    Example: get('mspang') -> {
                 'memberid': 3349,
                 'name': 'Michael Spang',
                 'program': 'Computer Science',
                 ...
             }
    """

    return connection.select_member_by_account(userid)


def get_studentid(studentid):
    """
    Look up attributes of a member by studnetid.

    Parameters:
        studentid - the student ID number

    Returns: a dictionary of attributes
    
    Example: get(...) -> {
                 'memberid': 3349,
                 'name': 'Michael Spang',
                 'program': 'Computer Science',
                 ...
             }
    """

    return connection.select_member_by_studentid(studentid)


def list_term(term):
    """
    Build a list of members in a term.

    Parameters:
        term - the term to match members against

    Returns: a list of member dictionaries

    Example: list_term('f2006'): -> [
                 { 'memberid': 3349, ... },
                 { 'memberid': ... }.
                 ...
             ]
    """

    # retrieve a list of memberids in term
    memberlist = connection.select_members_by_term(term)

    # convert the list of memberids to a list of dictionaries
    memberlist = map(connection.select_member_by_id, memberlist)

    return memberlist
        

def list_name(name):
    """
    Build a list of members with matching names.

    Parameters:
        name - the name to match members against

    Returns: a list of member dictionaries

    Example: list_name('Spang'): -> [
                 { 'memberid': 3349, ... },
                 { 'memberid': ... },
                 ...
             ]
    """

    # retrieve a list of memberids matching name
    memberlist = connection.select_members_by_name(name)

    # convert the list of memberids to a list of dictionaries
    memberlist = map(connection.select_member_by_id, memberlist)

    return memberlist


def delete(memberid):
    """
    Erase all records of a member.

    Note: real members are never removed
          from the database

    Parameters:
        memberid - the member id number

    Returns: attributes and terms of the
             member in a tuple

    Example: delete(0) -> ({ 'memberid': 0, name: 'Calum T. Dalek' ...}, ['s1993'])
    """

    # save member data
    member = connection.select_member_by_id(memberid)
    term_list = connection.select_terms(memberid)

    # remove data from the db
    connection.delete_term_all(memberid)
    connection.delete_member(memberid)
    connection.commit()

    return (member, term_list)


def update(member):
    """
    Update CSC member attributes. None is NULL.

    Parameters:
        member - a dictionary with member attributes as
                 returned by get, possibly omitting some
                 attributes. member['memberid'] must exist
                 and be valid.

    Exceptions:
        NoSuchMember       - if the member id does not exist
        InvalidStudentID   - if the student id number is malformed
        DuplicateStudentID - if the student id number exists 

    Example: update( {'memberid': 3349, userid: 'mspang'} )
    """

    if member.has_key('studentid') and member['studentid'] != None:

        studentid = member['studentid']
        
        # check the student id format
        regex = '^[0-9]{8}$'
        if studentid != None and not re.match(regex, str(studentid)):
            raise InvalidStudentID("student id is invalid: %s" % studentid)

        # check for duplicate student id
        member = connection.select_member_by_studentid(studentid)
        if member:
            raise DuplicateStudentID("student id exists in database: %s" %
                    studentid)

    # not specifying memberid is a bug
    if not member.has_key('memberid'):
        raise Exception("no member specified in call to update")
    memberid = member['memberid']

    # see if member exists
    old_member = connection.select_member_by_id(memberid)
    if not old_member:
        raise NoSuchMember("memberid does not exist in database: %d" %
                memberid)
    
    # do the update
    connection.update_member(member)

    # commit the transaction
    connection.commit()



### Term Table ###

def register(memberid, term_list):
    """
    Registers a member for one or more terms.

    Parameters:
        memberid  - the member id number
        term_list - the term to register for, or a list of terms

    Exceptions:
        InvalidTerm - if a term is malformed

    Example: register(3349, "w2007")

    Example: register(3349, ["w2007", "s2007"])
    """

    if not type(term_list) in (list, tuple):
        term_list = [ term_list ]

    for term in term_list:
        
        # check term syntax
        if not re.match('^[wsf][0-9]{4}$', term):
            raise InvalidTerm("term is invalid: %s" % term)
    
        # add term to database
        connection.insert_term(memberid, term)

    connection.commit()


def registered(memberid, term):
    """
    Determines whether a member is registered
    for a term.

    Parameters:
        memberid - the member id number
        term     - the term to check

    Returns: whether the member is registered

    Example: registered(3349, "f2006") -> True
    """

    return connection.select_term(memberid, term) != None


def terms_list(memberid):
    """
    Retrieves a list of terms a member is
    registered for.

    Parameters:
        memberid - the member id number

    Returns: list of term strings

    Example: registered(0) -> 's1993'
    """

    return connection.select_terms(memberid)



### Tests ###

if __name__ == '__main__':

    connect()
    
    
    sid = new("Test User", "99999999", "CS")

    assert registered(id, terms.current())
    print get(sid)
    register(sid, terms.next(terms.current()))
    assert registered(sid, terms.next(terms.current()))
    print terms_list(sid)
    print get(sid)
    print delete(sid)
