"""
CSC Member Management

This module contains functions for registering new members, registering
members for terms, searching for members, and other member-related
functions.

Transactions are used in each method that modifies the database. 
Future changes to the members database that need to be atomic
must also be moved into this module.
"""
import os, re, subprocess, ldap
from ceo import conf, ldapi, terms
from ceo.excep import InvalidArgument


### Configuration ###

CONFIG_FILE = '/etc/csc/accounts.cf'

cfg = {}

def configure():
    """Load Members Configuration"""

    string_fields = [ 'username_regex', 'shells_file', 'ldap_server_url',
            'ldap_users_base', 'ldap_groups_base', 'ldap_sasl_mech', 'ldap_sasl_realm',
            'expire_hook', 'mathsoc_regex', 'mathsoc_dont_count' ]
    numeric_fields = [ 'min_password_length' ]

    # read configuration file
    cfg_tmp = conf.read(CONFIG_FILE)

    # verify configuration
    conf.check_string_fields(CONFIG_FILE, string_fields, cfg_tmp)
    conf.check_integer_fields(CONFIG_FILE, numeric_fields, cfg_tmp)

    # update the current configuration with the loaded values
    cfg.update(cfg_tmp)



### Exceptions ###

class MemberException(Exception):
    """Base exception class for member-related errors."""
    def __init__(self, ex=None):
        Exception.__init__(self)
        self.ex = ex
    def __str__(self):
        return str(self.ex)

class InvalidTerm(MemberException):
    """Exception class for malformed terms."""
    def __init__(self, term):
        MemberException.__init__(self)
        self.term = term
    def __str__(self):
        return "Term is invalid: %s" % self.term

class NoSuchMember(MemberException):
    """Exception class for nonexistent members."""
    def __init__(self, memberid):
        MemberException.__init__(self)
        self.memberid = memberid
    def __str__(self):
        return "Member not found: %d" % self.memberid

class ChildFailed(MemberException):
    def __init__(self, program, status, output):
        MemberException.__init__(self)
        self.program, self.status, self.output = program, status, output
    def __str__(self):
        msg = '%s failed with status %d' % (self.program, self.status)
        if self.output:
            msg += ': %s' % self.output
        return msg


### Connection Management ###

# global directory connection
ld = None

def connect(auth_callback):
    """Connect to LDAP."""


    global ld
    password = None
    tries = 0
    while ld is None:
        try:
            ld = ldapi.connect_sasl(cfg['ldap_server_url'], cfg['ldap_sasl_mech'],
                cfg['ldap_sasl_realm'], password)
        except ldap.LOCAL_ERROR, e:
            tries += 1
            if tries > 3:
                raise e
            password = auth_callback.callback(e)
            if password == None:
                raise e


def disconnect():
    """Disconnect from LDAP."""

    global ld
    ld.unbind_s()
    ld = None


def connected():
    """Determine whether the connection has been established."""

    return ld and ld.connected()



### Members ###

def create_member(username, password, name, program):
    """
    Creates a UNIX user account with options tailored to CSC members.

    Parameters:
        username - the desired UNIX username
        password - the desired UNIX password
        name     - the member's real name
        program  - the member's program of study

    Exceptions:
        InvalidArgument - on bad account attributes provided

    Returns: the uid number of the new account

    See: create()
    """

    # check username format
    if not username or not re.match(cfg['username_regex'], username):
        raise InvalidArgument("username", username, "expected format %s" % repr(cfg['username_regex']))

    # check password length
    if not password or len(password) < cfg['min_password_length']:
        raise InvalidArgument("password", "<hidden>", "too short (minimum %d characters)" % cfg['min_password_length'])

    try:
        args = [ "/usr/bin/addmember", "--stdin", username, name, program ]
        addmember = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = addmember.communicate(password)
        status = addmember.wait()

        # # If the user was created, consider adding them to the mailing list
        # if not status:
        #     listadmin_cfg_file = "/path/to/the/listadmin/config/file"
        #     mail = subprocess.Popen(["/usr/bin/listadmin", "-f", listadmin_cfg_file, "--add-member", username + "@csclub.uwaterloo.ca"])
        #     status2 = mail.wait() # Fuck if I care about errors!
    except OSError, e:
        raise MemberException(e)

    if status:
        raise ChildFailed("addmember", status, out+err)


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

    return ldapi.lookup(ld, 'uid', userid, cfg['ldap_users_base'])

def uid2dn(uid):
    return 'uid=%s,%s' % (ldapi.escape(uid), cfg['ldap_users_base'])


def list_term(term):
    """
    Build a list of members in a term.

    Parameters:
        term - the term to match members against

    Returns: a list of members

    Example: list_term('f2006'): -> {
                 'uid=mspang, ou=...': { 'cn': 'Michael Spang', ... },
                 'uid=ctdalek, ou=...': { 'cn': 'Calum T. Dalek', ... },
                 ...
             }
    """

    members = ldapi.search(ld, cfg['ldap_users_base'],
            '(&(objectClass=member)(term=%s))', [ term ])
    return dict([(member[0], member[1]) for member in members])


def list_name(name):
    """
    Build a list of members with matching names.

    Parameters:
        name - the name to match members against

    Returns: a list of member dictionaries

    Example: list_name('Spang'): -> {
                 'uid=mspang, ou=...': { 'cn': 'Michael Spang', ... },
                 ...
             ]
    """

    members = ldapi.search(ld, cfg['ldap_users_base'],
            '(&(objectClass=member)(cn~=%s))', [ name ])
    return dict([(member[0], member[1]) for member in members])


def list_group(group):
    """
    Build a list of members in a group.

    Parameters:
        group - the group to match members against

    Returns: a list of member dictionaries

    Example: list_name('syscom'): -> {
                 'uid=mspang, ou=...': { 'cn': 'Michael Spang', ... },
                 ...
             ]
    """

    members = group_members(group)
    ret = {}
    if members:
        for member in members:
            info = get(member)
            if info:
                ret[uid2dn(member)] = info
    return ret


def list_all():
    """
    Build a list of all members

    Returns: a list of member dictionaries

    Example: list_name('Spang'): -> {
                 'uid=mspang, ou=...': { 'cn': 'Michael Spang', ... },
                 ...
             ]
    """

    members = ldapi.search(ld, cfg['ldap_users_base'], '(objectClass=member)')
    return dict([(member[0], member[1]) for member in members])


def list_positions():
    """
    Build a list of positions

    Returns: a list of positions and who holds them

    Example: list_positions(): -> {
                 'president': { 'mspang': { 'cn': 'Michael Spang', ... } } ],
                 ...
             ]
    """

    members = ld.search_s(cfg['ldap_users_base'], ldap.SCOPE_SUBTREE, '(position=*)')
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

    res = ld.search_s(cfg['ldap_users_base'], ldap.SCOPE_SUBTREE,
        '(&(objectClass=member)(position=%s))' % ldapi.escape(position))
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
            dn = 'uid=%s,%s' % (ldapi.escape(userid), cfg['ldap_users_base'])
            entry1 = {'position' : [position]}
            entry2 = {} #{'position' : []}
            entry = ()
            if action == 'del':
                entry = (entry1, entry2)
            elif action == 'add':
                entry = (entry2, entry1)
            mlist = ldapi.make_modlist(entry[0], entry[1])
            ld.modify_s(dn, mlist)


def change_group_member(action, group, userid):
    user_dn = 'uid=%s,%s' % (ldapi.escape(userid), cfg['ldap_users_base'])
    group_dn = 'cn=%s,%s' % (ldapi.escape(group), cfg['ldap_groups_base'])
    entry1 = {'uniqueMember' : []}
    entry2 = {'uniqueMember' : [user_dn]}
    entry = []
    if action == 'add' or action == 'insert':
        entry = (entry1, entry2)
    elif action == 'remove' or action == 'delete':
        entry = (entry2, entry1)
    else:
        raise InvalidArgument("action", action, "invalid action")
    mlist = ldapi.make_modlist(entry[0], entry[1])
    ld.modify_s(group_dn, mlist)



### Shells ###

def get_shell(userid):
    member = ldapi.lookup(ld, 'uid', userid, cfg['ldap_users_base'])
    if not member:
        raise NoSuchMember(userid)
    if 'loginShell' not in member:
        return
    return member['loginShell'][0]


def get_shells():
    return [ sh for sh in open(cfg['shells_file']).read().split("\n")
                if sh
                and sh[0] == '/'
                and not '#' in sh
                and os.access(sh, os.X_OK) ]


def set_shell(userid, shell):
    if not shell in get_shells():
        raise InvalidArgument("shell", shell, "is not in %s" % cfg['shells_file'])
    ldapi.modify(ld, 'uid', userid, cfg['ldap_users_base'], [ (ldap.MOD_REPLACE, 'loginShell', [ shell ]) ])



### Clubs ###

def create_club(username, name):
    """
    Creates a UNIX user account with options tailored to CSC-hosted clubs.
    
    Parameters:
        username - the desired UNIX username
        name     - the club name

    Exceptions:
        InvalidArgument - on bad account attributes provided

    Returns: the uid number of the new account

    See: create()
    """

    # check username format
    if not username or not re.match(cfg['username_regex'], username):
        raise InvalidArgument("username", username, "expected format %s" % repr(cfg['username_regex']))
    
    try:
        args = [ "/usr/bin/addclub", username, name ]
        addclub = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = addclub.communicate()
        status = addclub.wait()
    except OSError, e:
        raise MemberException(e)

    if status:
        raise ChildFailed("addclub", status, out+err)



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

    user_dn = 'uid=%s,%s' % (ldapi.escape(userid), cfg['ldap_users_base'])

    if type(term_list) in (str, unicode):
        term_list = [ term_list ]

    ldap_member = get(userid)
    if ldap_member and 'term' not in ldap_member:
        ldap_member['term'] = []

    if not ldap_member:
        raise NoSuchMember(userid)

    new_member = ldap_member.copy()
    new_member['term'] = new_member['term'][:]

    for term in term_list:

        # check term syntax
        if not re.match('^[wsf][0-9]{4}$', term):
            raise InvalidTerm(term)

        # add the term to the entry
        if not term in ldap_member['term']:
            new_member['term'].append(term)

    mlist = ldapi.make_modlist(ldap_member, new_member)
    ld.modify_s(user_dn, mlist)


def register_nonmember(userid, term_list):
    """Registers a non-member for one or more terms."""

    user_dn = 'uid=%s,%s' % (ldapi.escape(userid), cfg['ldap_users_base'])

    if type(term_list) in (str, unicode):
        term_list = [ term_list ]

    ldap_member = get(userid)
    if not ldap_member:
        raise NoSuchMember(userid)

    if 'term' not in ldap_member:
        ldap_member['term'] = []
    if 'nonMemberTerm' not in ldap_member:
        ldap_member['nonMemberTerm'] = []

    new_member = ldap_member.copy()
    new_member['nonMemberTerm'] = new_member['nonMemberTerm'][:]

    for term in term_list:

        # check term syntax
        if not re.match('^[wsf][0-9]{4}$', term):
            raise InvalidTerm(term)

        # add the term to the entry
        if not term in ldap_member['nonMemberTerm'] \
                and not term in ldap_member['term']:
            new_member['nonMemberTerm'].append(term)

    mlist = ldapi.make_modlist(ldap_member, new_member)
    ld.modify_s(user_dn, mlist)


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

    member = get(userid)
    if not member is None:
        return 'term' in member and term in member['term']
    else:
        return False


def group_members(group):

    """
    Returns a list of group members
    """

    group = ldapi.lookup(ld, 'cn', group, cfg['ldap_groups_base'])

    if group and 'uniqueMember' in group:
        r = re.compile('^uid=([^,]*)')
        return map(lambda x: r.match(x).group(1), group['uniqueMember'])
    return []

def expired_accounts():
    members = ldapi.search(ld, cfg['ldap_users_base'],
        '(&(objectClass=member)(!(|(term=%s)(nonMemberTerm=%s))))' %
        (terms.current(), terms.current()))
    return dict([(member[0], member[1]) for member in members])

def send_account_expired_email(name, email):
    args = [ cfg['expire_hook'], name, email ]
    os.spawnv(os.P_WAIT, cfg['expire_hook'], args)
