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
from csc.backends import db, ldapi
from csc.common import conf
from csc.common.excep import InvalidArgument


### Configuration ###

CONFIG_FILE = '/etc/csc/members.cf'

cfg = {}

def load_configuration():
    """Load Members Configuration"""

    string_fields = [ 'studentid_regex', 'realname_regex', 'server',
            'database', 'user', 'password', 'server_url', 'users_base',
            'groups_base', 'admin_bind_dn', 'admin_bind_pw' ]

    # read configuration file
    cfg_tmp = conf.read(CONFIG_FILE)

    # verify configuration
    conf.check_string_fields(CONFIG_FILE, string_fields, cfg_tmp)

    # update the current configuration with the loaded values
    cfg.update(cfg_tmp)



### Exceptions ###

DBException = db.DBException
ConfigurationException = conf.ConfigurationException

class MemberException(Exception):
    """Base exception class for member-related errors."""

class DuplicateStudentID(MemberException):
    """Exception class for student ID conflicts."""
    def __init__(self, studentid):
        self.studentid = studentid
    def __str__(self):
        return "Student ID already exists in the database: %s" % self.studentid

class InvalidStudentID(MemberException):
    """Exception class for malformed student IDs."""
    def __init__(self, studentid):
        self.studentid = studentid
    def __str__(self):
        return "Student ID is invalid: %s" % self.studentid

class InvalidTerm(MemberException):
    """Exception class for malformed terms."""
    def __init__(self, term):
        self.term = term
    def __str__(self):
        return "Term is invalid: %s" % self.term

class InvalidRealName(MemberException):
    """Exception class for invalid real names."""
    def __init__(self, name):
        self.name = name
    def __str__(self):
        return "Name is invalid: %s" % self.name

class NoSuchMember(MemberException):
    """Exception class for nonexistent members."""
    def __init__(self, memberid):
        self.memberid = memberid
    def __str__(self):
        return "Member not found: %d" % self.memberid



### Connection Management ###

# global database connection
db_connection = db.DBConnection()

# global directory connection
ldap_connection = ldapi.LDAPConnection()

def connect():
    """Connect to PostgreSQL."""

    load_configuration()
    db_connection.connect(cfg['server'], cfg['database'])
    ldap_connection.connect(cfg['server_url'], cfg['admin_bind_dn'], cfg['admin_bind_pw'], cfg['users_base'], cfg['groups_base'])


def disconnect():
    """Disconnect from PostgreSQL."""

    db_connection.disconnect()
    ldap_connection.disconnect()


def connected():
    """Determine whether the db_connection has been established."""

    return db_connection.connected() and ldap_connection.connected()



### Member Table ###

def new(uid, realname, studentid=None, program=None, mtype='user'):
    """
    Registers a new CSC member. The member is added to the members table
    and registered for the current term.

    Parameters:
        uid       - the initial user id
        realname  - the full real name of the member
        studentid - the student id number of the member
        program   - the program of study of the member
        mtype     - a string describing the type of member ('user', 'club')

    Returns: the memberid of the new member

    Exceptions:
        DuplicateStudentID - if the student id already exists in the database
        InvalidStudentID   - if the student id is malformed
        InvalidRealName    - if the real name is malformed

    Example: new("Michael Spang", program="CS") -> 3349
    """

    # blank attributes should be NULL
    if studentid == '': studentid = None
    if program == '': program = None
    if uid == '': uid = None
    if mtype == '': mtype = None

    # check the student id format
    if studentid is not None and not re.match(cfg['studentid_regex'], str(studentid)):
        raise InvalidStudentID(studentid)

    # check real name format (UNIX account real names must not contain [,:=])
    if not re.match(cfg['realname_regex'], realname):
        raise InvalidRealName(realname)

    # check for duplicate student id
    member = db_connection.select_member_by_studentid(studentid) or \
            ldap_connection.member_search_studentid(studentid)
    if member:
        raise DuplicateStudentID(studentid)

    # check for duplicate userid
    member = db_connection.select_member_by_userid(uid) or \
            ldap_connection.user_lookup(uid)
    if member:
        raise InvalidArgument("uid", uid, "duplicate uid")

    # add the member to the database
    memberid = db_connection.insert_member(realname, studentid, program, userid=uid)

    # add the member to the directory
    ldap_connection.member_add(uid, realname, studentid, program)

    # register them for this term in the database
    db_connection.insert_term(memberid, terms.current())

    # register them for this term in the directory
    member = ldap_connection.member_lookup(uid)
    member['term'] = [ terms.current() ]
    ldap_connection.user_modify(uid, member)

    # commit the database transaction
    db_connection.commit()

    return memberid


def get(memberid):
    """
    Look up attributes of a member by memberid.

    Returns: a dictionary of attributes

    Example: get(3349) -> {
                 'memberid': 3349,
                 'name': 'Michael Spang',
                 'program': 'Computer Science',
                 ...
             }
    """

    return db_connection.select_member_by_id(memberid)


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

    return db_connection.select_member_by_userid(userid)


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

    return db_connection.select_member_by_studentid(studentid)


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
    memberlist = db_connection.select_members_by_term(term)

    return memberlist.values()


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
    memberlist = db_connection.select_members_by_name(name)

    return memberlist.values()


def list_all():
    """
    Builds a list of all members.
    
    Returns: a list of member dictionaries
    """

    # retrieve a list of members
    memberlist = db_connection.select_all_members()

    return memberlist.values()


def delete(memberid):
    """
    Erase all records of a member.

    Note: real members are never removed from the database

    Returns: attributes and terms of the member in a tuple

    Exceptions:
        NoSuchMember - if the member id does not exist

    Example: delete(0) -> ({ 'memberid': 0, name: 'Calum T. Dalek' ...}, ['s1993'])
    """

    # save member data
    member = db_connection.select_member_by_id(memberid)

    # bail if not found
    if not member:
        raise NoSuchMember(memberid)

    term_list = db_connection.select_terms(memberid)

    # remove data from the db
    db_connection.delete_term_all(memberid)
    db_connection.delete_member(memberid)
    db_connection.commit()

    # remove data from the directory
    if member and member['userid']:
        uid = member['userid']
        ldap_connection.user_delete(uid)

    return (member, term_list)


def update(member):
    """
    Update CSC member attributes.

    Parameters:
        member - a dictionary with member attributes as returned by get,
                 possibly omitting some attributes. member['memberid']
                 must exist and be valid. None is NULL.

    Exceptions:
        NoSuchMember       - if the member id does not exist
        InvalidStudentID   - if the student id number is malformed
        DuplicateStudentID - if the student id number exists 

    Example: update( {'memberid': 3349, userid: 'mspang'} )
    """

    if member.has_key('studentid') and member['studentid'] is not None:

        studentid = member['studentid']
        
        # check the student id format
        if studentid is not None and not re.match(cfg['studentid_regex'], str(studentid)):
            raise InvalidStudentID(studentid)

        # check for duplicate student id
        dupmember = db_connection.select_member_by_studentid(studentid)
        if dupmember:
            raise DuplicateStudentID(studentid)

    # not specifying memberid is a bug
    if not member.has_key('memberid'):
        raise Exception("no member specified in call to update")
    memberid = member['memberid']

    # see if member exists
    if not get(memberid):
        raise NoSuchMember(memberid)

    # do the update
    db_connection.update_member(member)

    # commit the transaction
    db_connection.commit()



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

    if type(term_list) in (str, unicode):
        term_list = [ term_list ]

    ldap_member = None
    db_member = get(memberid)
    if db_member['userid']:
        uid = db_member['userid']
        ldap_member = ldap_connection.member_lookup(uid)
        if ldap_member and 'term' not in ldap_member:
            ldap_member['term'] = []

    for term in term_list:

        # check term syntax
        if not re.match('^[wsf][0-9]{4}$', term):
            raise InvalidTerm(term)

        # add term to database
        db_connection.insert_term(memberid, term)

        # add the term to the directory
        if ldap_member:
            ldap_member['term'].append(term)

    if ldap_member:
        ldap_connection.user_modify(uid, ldap_member)

    db_connection.commit()


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

    return db_connection.select_term(memberid, term) is not None


def member_terms(memberid):
    """
    Retrieves a list of terms a member is
    registered for.

    Parameters:
        memberid - the member id number

    Returns: list of term strings

    Example: registered(0) -> 's1993'
    """

    terms_list = db_connection.select_terms(memberid)
    terms_list.sort(terms.compare)
    return terms_list



### Tests ###

if __name__ == '__main__':

    from csc.common.test import *

    # t=test m=member s=student u=updated
    tmname = 'Test Member'
    tmuid = 'testmember'
    tmprogram = 'Metaphysics'
    tmsid = '00000000'
    tm2name = 'Test Member 2'
    tm2uid = 'testmember2'
    tm2sid = '00000001'
    tm2uname = 'Test Member II'
    tm2usid = '00000002'
    tm2uprogram = 'Pseudoscience'

    tmdict = {'name': tmname, 'userid': tmuid, 'program': tmprogram, 'type': 'user', 'studentid': tmsid }
    tm2dict = {'name': tm2name, 'userid': tm2uid, 'program': None, 'type': 'user', 'studentid': tm2sid }
    tm2udict = {'name': tm2uname, 'userid': tm2uid, 'program': tm2uprogram, 'type': 'user', 'studentid': tm2usid }

    thisterm = terms.current()
    nextterm = terms.next(thisterm)

    test(connect)
    connect()
    success()

    test(connected)
    assert_equal(True, connected())
    success()

    dmid = get_studentid(tmsid)
    if dmid: delete(dmid['memberid'])
    dmid = get_studentid(tm2sid)
    if dmid: delete(dmid['memberid'])
    dmid = get_studentid(tm2usid)
    if dmid: delete(dmid['memberid'])

    test(new)
    tmid = new(tmuid, tmname, tmsid, tmprogram)
    tm2id = new(tm2uid, tm2name, tm2sid)
    success()

    tmdict['memberid'] = tmid
    tm2dict['memberid'] = tm2id
    tm2udict['memberid'] = tm2id

    test(registered)
    assert_equal(True, registered(tmid, thisterm))
    assert_equal(True, registered(tm2id, thisterm))
    assert_equal(False, registered(tmid, nextterm))
    success()

    test(get)
    assert_equal(tmdict, get(tmid))
    assert_equal(tm2dict, get(tm2id))
    success()

    test(list_name)
    assert_equal(True, tmid in [ x['memberid'] for x in list_name(tmname) ])
    assert_equal(True, tm2id in [ x['memberid'] for x in list_name(tm2name) ])
    success()

    test(list_all)
    allmembers = list_all()
    assert_equal(True, tmid in [ x['memberid'] for x in allmembers ])
    assert_equal(True, tm2id in [ x['memberid'] for x in allmembers ])
    success()

    test(register)
    register(tmid, nextterm)
    assert_equal(True, registered(tmid, nextterm))
    success()

    test(member_terms)
    assert_equal([thisterm, nextterm], member_terms(tmid))
    assert_equal([thisterm], member_terms(tm2id))
    success()

    test(list_term)
    assert_equal(True, tmid in [ x['memberid'] for x in list_term(thisterm) ])
    assert_equal(True, tmid in [ x['memberid'] for x in list_term(nextterm) ])
    assert_equal(True, tm2id in [ x['memberid'] for x in list_term(thisterm) ])
    assert_equal(False, tm2id in [ x['memberid'] for x in list_term(nextterm) ])
    success()

    test(update)
    update(tm2udict)
    assert_equal(tm2udict, get(tm2id))
    success()

    test(get_userid)
    assert_equal(tm2udict, get_userid(tm2uid))
    success()

    test(get_studentid)
    assert_equal(tm2udict, get_studentid(tm2usid))
    assert_equal(tmdict, get_studentid(tmsid))
    success()

    test(delete)
    delete(tmid)
    delete(tm2id)
    success()

    test(disconnect)
    disconnect()
    assert_equal(False, connected())
    disconnect()
    success()
