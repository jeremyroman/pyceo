"""
CSC Member Management

This module contains functions for registering new members, registering
members for terms, searching for members, and other member-related
functions.

Transactions are used in each method that modifies the database. 
Future changes to the members database that need to be atomic
must also be moved into this module.
"""
import re, ldap
from csc.adm import terms
from csc.backends import ldapi
from csc.common import conf
from csc.common.excep import InvalidArgument


### Configuration ###

CONFIG_FILE = '/etc/csc/members.cf'

cfg = {}

def load_configuration():
    """Load Members Configuration"""

    string_fields = [ 'realname_regex', 'server_url', 'users_base',
            'groups_base', 'sasl_mech', 'sasl_realm', 'admin_bind_keytab',
            'admin_bind_userid' ]

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

class InvalidTerm(MemberException):
    """Exception class for malformed terms."""
    def __init__(self, term):
        self.term = term
    def __str__(self):
        return "Term is invalid: %s" % self.term

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
    """Connect to LDAP."""

    load_configuration()
    ldap_connection.connect_sasl(cfg['server_url'], cfg['sasl_mech'],
        cfg['sasl_realm'], cfg['admin_bind_userid'],
        ('keytab', cfg['admin_bind_keytab']), cfg['users_base'],
        cfg['groups_base'])

def disconnect():
    """Disconnect from LDAP."""

    ldap_connection.disconnect()


def connected():
    """Determine whether the connection has been established."""

    return ldap_connection.connected()



### Members ###

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


def list_group(group):
    """
    Build a list of members in a group.

    Parameters:
        group - the group to match members against

    Returns: a list of member dictionaries

    Example: list_name('syscom'): -> {
                 'mspang': { 'cn': 'Michael Spang', ... },
                 ...
             ]
    """

    members = group_members(group)
    ret = {}
    if members:
        for member in members:
            info = get(member)
            if info:
                ret[member] = info
    return ret


def list_positions():
    """
    Build a list of positions

    Returns: a list of positions and who holds them

    Example: list_positions(): -> {
                 'president': { 'mspang': { 'cn': 'Michael Spang', ... } } ],
                 ...
             ]
    """

    ceo_ldap = ldap_connection.ldap
    user_base = ldap_connection.user_base

    members = ceo_ldap.search_s(user_base, ldap.SCOPE_SUBTREE, '(position=*)')
    positions = {}
    for (_, member) in members:
        for position in member['position']:
            if not position in positions:
                positions[position] = {}
            positions[position][member['uid'][0]] = member
    return positions

def set_position(position, members):
    """
    Sets a position

    Parameters:
        position - the position to set
        members - an array of members that hold the position

    Example: set_position('president', ['dtbartle'])
    """

    ceo_ldap = ldap_connection.ldap
    user_base = ldap_connection.user_base
    escape = ldap_connection.escape

    res = ceo_ldap.search_s(user_base, ldap.SCOPE_SUBTREE,
        '(&(objectClass=member)(position=%s))' % escape(position))
    old = set([ member['uid'][0] for (_, member) in res ])
    new = set(members)
    mods = {
        'del': set(old) - set(new),
        'add': set(new) - set(old),
    }
    if len(mods['del']) == 0 and len(mods['add']) == 0:
        return

    for action in ['del', 'add']:
        for userid in mods[action]:
            dn = 'uid=%s,%s' % (escape(userid), user_base)
            entry1 = {'position' : [position]}
            entry2 = {} #{'position' : []}
            entry = ()
            if action == 'del':
                entry = (entry1, entry2)
            elif action == 'add':
                entry = (entry2, entry1)
            mlist = ldap_connection.make_modlist(entry[0], entry[1])
            ceo_ldap.modify_s(dn, mlist)


def change_group_member(action, group, userid):

    ceo_ldap = ldap_connection.ldap
    user_base = ldap_connection.user_base
    group_base = ldap_connection.group_base
    escape = ldap_connection.escape

    user_dn = 'uid=%s,%s' % (escape(userid), user_base)
    group_dn = 'cn=%s,%s' % (escape(group), group_base)
    entry1 = {'uniqueMember' : []}
    entry2 = {'uniqueMember' : [user_dn]}
    entry = []
    if action == 'add' or action == 'insert':
        entry = (entry1, entry2)
    elif action == 'remove' or action == 'delete':
        entry = (entry2, entry1)
    else:
        raise InvalidArgument("action", action, "invalid action")
    mlist = ldap_connection.make_modlist(entry[0], entry[1])
    ceo_ldap.modify_s(group_dn, mlist)


### Terms ###

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


def group_members(group):

    """
    Returns a list of group members
    """

    group = ldap_connection.group_lookup(group)
    if group:
        if 'uniqueMember' in group:
            r = re.compile('^uid=([^,]*)')
            return map(lambda x: r.match(x).group(1), group['uniqueMember'])
        elif 'memberUid' in group:
            return group['memberUid']
        else:
            return []
    else:
        return []
