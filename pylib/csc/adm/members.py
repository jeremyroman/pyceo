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
from csc.backends import ldapi
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

# global directory connection
ldap_connection = ldapi.LDAPConnection()

def connect():
    """Connect to PostgreSQL."""

    load_configuration()
    ldap_connection.connect(cfg['server_url'], cfg['admin_bind_dn'], cfg['admin_bind_pw'], cfg['users_base'], cfg['groups_base'])


def disconnect():
    """Disconnect from PostgreSQL."""

    ldap_connection.disconnect()


def connected():
    """Determine whether the connection has been established."""

    return ldap_connection.connected()



### Member Table ###

def new(uid, realname, studentid=None, program=None):
    """
    Registers a new CSC member. The member is added to the members table
    and registered for the current term.

    Parameters:
        uid       - the initial user id
        realname  - the full real name of the member
        studentid - the student id number of the member
        program   - the program of study of the member

    Returns: the username of the new member

    Exceptions:
        DuplicateStudentID - if the student id already exists in the database
        InvalidStudentID   - if the student id is malformed
        InvalidRealName    - if the real name is malformed

    Example: new("Michael Spang", program="CS") -> "mspang"
    """

    # blank attributes should be NULL
    if studentid == '': studentid = None
    if program == '': program = None
    if uid == '': uid = None

    # check the student id format
    if studentid is not None and not re.match(cfg['studentid_regex'], str(studentid)):
        raise InvalidStudentID(studentid)

    # check real name format (UNIX account real names must not contain [,:=])
    if not re.match(cfg['realname_regex'], realname):
        raise InvalidRealName(realname)

    # check for duplicate student id
    member = ldap_connection.member_search_studentid(studentid)
    if member:
        raise DuplicateStudentID(studentid)

    # check for duplicate userid
    member = ldap_connection.user_lookup(uid)
    if member:
        raise InvalidArgument("uid", uid, "duplicate uid")

    # add the member to the directory
    ldap_connection.member_add(uid, realname, studentid, program)

    # register them for this term in the directory
    member = ldap_connection.member_lookup(uid)
    member['term'] = [ terms.current() ]
    ldap_connection.user_modify(uid, member)

    return uid


def get(userid):
    """
    Look up attributes of a member by userid.

    Returns: a dictionary of attributes

    Example: get('mspang') -> {
                 'cn': [ 'Michael Spang' ],
                 'program': [ 'Computer Science' ],
                 ...
             }
    """

    return ldap_connection.user_lookup(userid)


def get_studentid(studentid):
    """
    Look up attributes of a member by studentid.

    Parameters:
        studentid - the student ID number

    Returns: a dict of members
    
    Example: get(...) -> {
                'mspang': {
                    'name': [ 'Michael Spang' ],
                    'program': [ 'Computer Science' ],
                 }
                 ...
             }
    """

    return ldap_connection.member_search_studentid(studentid)


def list_term(term):
    """
    Build a list of members in a term.

    Parameters:
        term - the term to match members against

    Returns: a list of members

    Example: list_term('f2006'): -> {
                 'mspang': { 'cn': 'Michael Spang', ... },
                 'ctdalek': { 'cn': 'Calum T. Dalek', ... },
                 ...
             }
    """

    return ldap_connection.member_search_term(term)


def list_name(name):
    """
    Build a list of members with matching names.

    Parameters:
        name - the name to match members against

    Returns: a list of member dictionaries

    Example: list_name('Spang'): -> {
                 'mspang': { 'cn': 'Michael Spang', ... },
                 ...
             ]
    """

    return ldap_connection.member_search_name(name)


def delete(userid):
    """
    Erase all records of a member.

    Note: real members are never removed from the database

    Returns: ldap entry of the member

    Exceptions:
        NoSuchMember - if the user id does not exist

    Example: delete('ctdalek') -> { 'cn': [ 'Calum T. Dalek' ], 'term': ['s1993'], ... }
    """

    # save member data
    member = ldap_connection.user_lookup(userid)

    # bail if not found
    if not member:
        raise NoSuchMember(userid)

    # remove data from the directory
    uid = member['uid'][0]
    ldap_connection.user_delete(uid)

    return member



### Term Table ###

def register(userid, term_list):
    """
    Registers a member for one or more terms.

    Parameters:
        userid  - the member's username
        term_list - the term to register for, or a list of terms

    Exceptions:
        InvalidTerm - if a term is malformed

    Example: register(3349, "w2007")

    Example: register(3349, ["w2007", "s2007"])
    """

    if type(term_list) in (str, unicode):
        term_list = [ term_list ]

    ldap_member = ldap_connection.member_lookup(userid)
    if ldap_member and 'term' not in ldap_member:
        ldap_member['term'] = []

    if not ldap_member:
        raise NoSuchMember(userid)

    for term in term_list:

        # check term syntax
        if not re.match('^[wsf][0-9]{4}$', term):
            raise InvalidTerm(term)

        # add the term to the directory
        ldap_member['term'].append(term)

    ldap_connection.user_modify(userid, ldap_member)


def registered(userid, term):
    """
    Determines whether a member is registered
    for a term.

    Parameters:
        userid   - the member's username
        term     - the term to check

    Returns: whether the member is registered

    Example: registered("mspang", "f2006") -> True
    """

    member = ldap_connection.member_lookup(userid)
    return 'term' in member and term in member['term']


def member_terms(userid):
    """
    Retrieves a list of terms a member is
    registered for.

    Parameters:
        userid - the member's username

    Returns: list of term strings

    Example: registered('ctdalek') -> 's1993'
    """

    member = ldap_connection.member_lookup(userid)
    if not 'term' in member:
        return []
    else:
        return member['term']



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

    tmdict = {'cn': [tmname], 'uid': [tmuid], 'program': [tmprogram], 'studentid': [tmsid] }
    tm2dict = {'cn': [tm2name], 'uid': [tm2uid], 'studentid': [tm2sid] }
    tm2udict = {'cn': [tm2uname], 'uid': [tm2uid], 'program': [tm2uprogram], 'studentid': [tm2usid] }

    thisterm = terms.current()
    nextterm = terms.next(thisterm)

    test(connect)
    connect()
    success()

    test(connected)
    assert_equal(True, connected())
    success()

    dmid = get_studentid(tmsid)
    if tmuid in dmid: delete(dmid[tmuid]['uid'][0])
    dmid = get_studentid(tm2sid)
    if tm2uid in dmid: delete(dmid[tm2uid]['uid'][0])
    dmid = get_studentid(tm2usid)
    if tm2uid in dmid: delete(dmid[tm2uid]['uid'][0])

    test(new)
    tmid = new(tmuid, tmname, tmsid, tmprogram)
    tm2id = new(tm2uid, tm2name, tm2sid)
    success()

    test(registered)
    assert_equal(True, registered(tmid, thisterm))
    assert_equal(True, registered(tm2id, thisterm))
    assert_equal(False, registered(tmid, nextterm))
    success()

    test(get)
    tmp = get(tmid)
    del tmp['objectClass']
    del tmp['term']
    assert_equal(tmdict, tmp)
    tmp = get(tm2id)
    del tmp['objectClass']
    del tmp['term']
    assert_equal(tm2dict, tmp)
    success()

    test(list_name)
    assert_equal(True, tmid in list_name(tmname).keys())
    assert_equal(True, tm2id in list_name(tm2name).keys())
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
    assert_equal(True, tmid in list_term(thisterm).keys())
    assert_equal(True, tmid in list_term(nextterm).keys())
    assert_equal(True, tm2id in list_term(thisterm).keys())
    assert_equal(False, tm2id in list_term(nextterm).keys())
    success()

    test(get)
    tmp = get(tm2id)
    del tmp['objectClass']
    del tmp['term']
    assert_equal(tm2dict, tmp)
    success()

    test(get_studentid)
    tmp = get_studentid(tm2sid)[tm2uid]
    del tmp['objectClass']
    del tmp['term']
    assert_equal(tm2dict, tmp)
    tmp = get_studentid(tmsid)[tmuid]
    del tmp['objectClass']
    del tmp['term']
    assert_equal(tmdict, tmp)
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
