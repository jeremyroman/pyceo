"""
UNIX Accounts Administration

This module contains functions for creating, deleting, and manipulating
UNIX user accounts and account groups in the CSC LDAP directory.
"""
import re, pwd, grp, os, subprocess
from csc.common import conf
from csc.common.excep import InvalidArgument
from csc.backends import ldapi, krb


### Configuration ###

CONFIG_FILE = '/etc/csc/accounts.cf'

cfg = {}

def configure():
    """Helper to load the accounts configuration. You need not call this."""

    string_fields = [ 'member_shell', 'member_home', 'member_desc',
            'member_group', 'club_shell', 'club_home', 'club_desc',
            'club_group', 'admin_shell', 'admin_home', 'admin_desc',
            'admin_group', 'group_desc', 'username_regex', 'groupname_regex',
            'shells_file', 'server_url', 'users_base', 'groups_base',
            'sasl_mech', 'sasl_realm', 'admin_bind_keytab',
            'admin_bind_userid', 'realm', 'admin_principal', 'admin_keytab' ]
    numeric_fields = [ 'member_min_id', 'member_max_id', 'club_min_id',
            'club_max_id', 'admin_min_id', 'admin_max_id', 'group_min_id',
            'group_max_id', 'min_password_length' ]

    # read configuration file
    cfg_tmp = conf.read(CONFIG_FILE)

    # verify configuration (not necessary, but prints a useful error)
    conf.check_string_fields(CONFIG_FILE, string_fields, cfg_tmp)
    conf.check_integer_fields(CONFIG_FILE, numeric_fields, cfg_tmp)

    # update the current configuration with the loaded values
    cfg.update(cfg_tmp)



### Exceptions  ###

KrbException = krb.KrbException
LDAPException = ldapi.LDAPException
ConfigurationException = conf.ConfigurationException

class AccountException(Exception):
    """Base exception class for account-related errors."""

class NoAvailableIDs(AccountException):
    """Exception class for exhausted userid ranges."""
    def __init__(self, minid, maxid):
        self.minid, self.maxid = minid, maxid
    def __str__(self):
        return "No free ID pairs found in range [%d, %d]" % (self.minid, self.maxid)

class NameConflict(AccountException):
    """Exception class for name conflicts with existing accounts/groups."""
    def __init__(self, name, nametype, source):
        self.name, self.nametype, self.source = name, nametype, source
    def __str__(self):
        return 'Name Conflict: %s "%s" already exists in %s' % (self.nametype, self.name, self.source)

class NoSuchAccount(AccountException):
    """Exception class for missing LDAP entries for accounts."""
    def __init__(self, account, source):
        self.account, self.source = account, source
    def __str__(self):
        return 'Account "%s" not found in %s' % (self.account, self.source)

class NoSuchGroup(AccountException):
    """Exception class for missing LDAP entries for groups."""
    def __init__(self, account, source):
        self.account, self.source = account, source
    def __str__(self):
        return 'Account "%s" not found in %s' % (self.account, self.source)

class ChildFailed(AccountException):
    def __init__(self, program, status, output):
        self.program, self.status, self.output = program, status, output
    def __str__(self):
        msg = '%s failed with status %d' % (self.program, self.status)
        if self.output:
            msg += ': %s' % self.output
        return msg


### Connection Management ###

ldap_connection = ldapi.LDAPConnection()
krb_connection = krb.KrbConnection()

def connect():
    """Connect to LDAP and Kerberos and load configuration. You must call before anything else."""

    configure()

    # connect to the LDAP server
    ldap_connection.connect_sasl(cfg['server_url'], cfg['sasl_mech'],
        cfg['sasl_realm'], cfg['admin_bind_userid'],
        ('keytab', cfg['admin_bind_keytab']), cfg['users_base'],
        cfg['groups_base'])

    # connect to the Kerberos master server
    krb_connection.connect(cfg['admin_principal'], cfg['admin_keytab'])


def disconnect():
    """Disconnect from LDAP and Kerberos. Call this before quitting."""

    ldap_connection.disconnect()
    krb_connection.disconnect()


def connected():
    """Determine whether a connection has been established."""

    return ldap_connection.connected() and krb_connection.connected()



### General Account Management ###

def create(username, name, minimum_id, maximum_id, home, password=None, description='', gecos='', shell=None, group=None):
    """
    Creates a UNIX user account. This involves first creating an LDAP
    directory entry, then creating a Kerberos principal.

    The UID/GID namespace may be divided into ranges according to account type
    or purpose. This function requires such a range to allocate ids from.

    If no password is specified or password is None, no Kerberos principal
    will be created and the account will not be capable of direct login.
    This is desirable for administrative and club accounts.

    If no group is specified, a new group will be created with the same name
    as the user. The uid of the created user and gid of the created group
    will be numerically equal. There is generally no reason to specify a
    group. Furthermore, only groups present in the directory are allowed.

    If an account is relevant to only one system and will not own files on
    NFS, please use adduser(8) on the relevant system instead.

    Generally do not directly use this function. The create_member(),
    create_club(), and create_adm() functions will fill in most of
    the details for you and may do additional checks.

    Parameters:
        username    - UNIX username for the account
        name        - common name LDAP attribute
        minimum_id  - the smallest UID/GID to assign
        maximum_id  - the largest UID/GID to assign
        home        - home directory LDAP attribute
        password    - password for the account
        description - description LDAP attribute
        gecos       - gecos LDAP attribute
        shell       - user shell LDAP attribute
        group       - primary group for account

    Exceptions:
        NameConflict     - when the name conflicts with an existing account
        NoSuchGroup      - when the group parameter corresponds to no group
        NoAvailableIDs   - when the ID range is exhausted
        AccountException - when not connected

    Returns: the uid number of the new account

    Example: create('mspang', 'Michael Spang', 20000, 39999,
                 '/users/mspang', 'secret', 'CSC Member Account',
                 build_gecos('Michael Spang', other='3349'),
                 '/bin/bash', 'users')
    """
 
    # check connection
    if not connected():
        raise AccountException("Not connected to LDAP and Kerberos")

    # check for path characters in username (. and /)
    if re.search('[\\./]', username):
        raise InvalidArgument("username", username, "invalid characters")

    check_name_usage(username)

    # determine the first available userid
    userid = first_available_id(minimum_id, maximum_id)
    if not userid:
        raise NoAvailableIDs(minimum_id, maximum_id)

    # determine the account's default group
    if group: 
        group_data = ldap_connection.group_lookup(group)
        if not group_data:
            raise NoSuchGroup(group, "LDAP")
        gid = int(group_data['gidNumber'][0])
    else:
        gid = userid

    ### User creation ###

    if not ldap_connection.user_lookup(username):

        # create the LDAP entry
        ldap_connection.account_add(username, name, userid, gid, home, shell, gecos, description)

    else:

        # add the required attribute to the LDAP entry
        ldap_connection.member_add_account(username, userid, gid, home, shell, gecos)

    # create a user group if no other group was specified
    if not group:
        ldap_connection.group_add(username, gid)

    # create the Kerberos principal
    if password:    
        principal = username + '@' + cfg['realm']
        krb_connection.add_principal(principal, password)

    return userid


def delete(username):
    """
    Deletes a UNIX account. Both LDAP entries and Kerberos principals that
    match username are deleted. A group with the same name is deleted too,
    if it exists and has the same id as the account.

    Returns: tuple with deleted LDAP and Kerberos information
             note: the Kerberos keys are not recoverable 
    """

    # check connection
    if not connected():
        raise AccountException("Not connected to LDAP and Kerberos")

    # build principal name from username
    principal = username + '@' + cfg['realm']

    # get account state 
    ldap_state = ldap_connection.user_lookup(username)
    krb_state = krb_connection.get_principal(principal)
    group_state = ldap_connection.group_lookup(username)

    # don't delete group unless the gid matches the account's uid
    if not ldap_state or group_state and ldap_state['uidNumber'][0] != group_state['gidNumber'][0]:
        group_state = None

    # fail if no data is found in either LDAP or Kerberos
    if not ldap_state and not krb_state:
        raise NoSuchAccount(username, "LDAP/Kerberos")

    ### User deletion ###

    # delete the LDAP entries
    if ldap_state:
        ldap_connection.user_delete(username)
    if group_state:
        ldap_connection.group_delete(username)

    # delete the Kerberos principal
    if krb_state:
        krb_connection.delete_principal(principal)

    return ldap_state, group_state, krb_state


def status(username):
    """
    Checks if an account exists.

    Returns: a boolean 2-tuple (exists, has_password)
    """

    ldap_state = ldap_connection.account_lookup(username)
    krb_state = krb_connection.get_principal(username)
    return (ldap_state is not None, krb_state is not None)


def add_password(username, password):
    """
    Creates a principal for an existing, passwordless account.

    Parameters:
        username - a UNIX account username
        password - a password for the acccount
    """
    check_account_status(username)
    ldap_state = ldap_connection.user_lookup(username)
    if int(ldap_state['uidNumber'][0]) < 1000:
        raise AccountException("Attempted to add password to a system account")
    krb_connection.add_principal(username, password)


def reset_password(username, newpassword):
    """
    Changes a user's password.

    Parameters:
        username    - a UNIX account username
        newpassword - a new password for the account
    """
    check_account_status(username, require_krb=True)
    krb_connection.change_password(username, newpassword)


def get_uid(username):
    """
    Determine the numeric uid of an account.

    Returns: a uid as an int
    """
    check_account_status(username)
    account_data = ldap_connection.user_lookup(username)
    return int(account_data['uidNumber'][0])


def get_gid(username):
    """
    Determine the numeric gid of an account (default group).

    Returns: a gid as an int
    """
    check_account_status(username)
    account_data = ldap_connection.user_lookup(username)
    return int(account_data['gidNumber'][0])


def get_gecos(username, account_data=None):
    """
    Retrieve GECOS information of a user.

    Returns: raw gecos data as a string, or None
    """
    check_account_status(username)
    if not account_data:
        account_data = ldap_connection.user_lookup(username)
    if 'gecos' in account_data:
        return account_data['gecos'][0]
    else:
        return None
    

def update_gecos(username, gecos_data):
    """
    Set GECOS information for a user. The LDAP 'cn' attribute
    is also updated with the user's full name.

    See build_gecos() and parse_gecos() for help dealing with
    the chfn(1) GECOS format.

    Use update_name() to update the name porition, as it will update
    the LDAP 'cn' atribute as well.

    Parameters:
        username   - a UNIX account username
        gecos_data - a raw gecos string

    Example: update_gecos('mspang', build_gecos('Mike Spang'))
    """
    check_account_status(username)
    entry = ldap_connection.user_lookup(username)
    entry['gecos'] = [ gecos_data ]
    ldap_connection.user_modify(username, entry)


def get_name(username):
    """
    Get the real name of a user. Note that this name is usually stored
    in both the 'cn' attribute and the 'gecos' attribute, and they
    may differ. This function will always return the first in the'cn'
    version. If there are multiple, the first in the list is returned.

    Returns: the common name associated with the account
    """
    check_account_status(username)
    account_data = ldap_connection.user_lookup(username)
    return account_data['cn'][0]


def update_name(username, name, update_gecos=True):
    """
    Set the real name of a user. This name will be updated in both
    the GECOS field and the common name field. If there are multiple
    common names, they will *all* be overwritten with the provided name.

    Parameters:
        username     - the UNIX account usernmae
        nane         - new real name for the account
        update_gecos - whether to update gecos field
    """
    check_account_status(username)
    account_data = ldap_connection.user_lookup(username)
    account_data['cn'] = [ name ]
    if update_gecos:
        gecos_dict = parse_gecos(get_gecos(username, account_data))
        gecos_dict['fullname'] = name
        account_data['gecos'] = [ build_gecos(**gecos_dict) ]
    ldap_connection.user_modify(username, account_data)


def get_shell(username):
    """
    Retrieve a user's shell.

    Returns: the path to the shell, or None
    """
    check_account_status(username)
    account_data = ldap_connection.user_lookup(username)
    if 'loginShell' not in account_data or len(account_data['loginShell']) < 1:
        return None
    return account_data['loginShell'][0]


def update_shell(username, shell, check=True):
    """
    Set a user's shell.

    Parameters:
        username - the UNIX account username
        shell    - the new shell for the user
        check    - whether to check if the shell is in the shells file

    Exceptions:
        InvalidArgument - on nonexistent shell
    """

    # reject nonexistent or nonexecutable shells
    if not os.access(shell, os.X_OK) or not os.path.isfile(shell):
        raise InvalidArgument("shell", shell, "not an executable file")

    if check:
        
        # load shells file
        shells = open(cfg['shells_file']).read().split("\n")
        shells = [ x for x in shells if x and x[0] == '/' and '#' not in x ]

        # reject shells that aren't in the shells file (usually /etc/shells)
        if check and shell not in shells:
            raise InvalidArgument("shell", shell, "is not in %s" % cfg['shells_file'])
    
    check_account_status(username)
    account_data = ldap_connection.user_lookup(username)
    account_data['loginShell'] = [ shell ]
    ldap_connection.user_modify(username, account_data)
    

def get_home(username):
    """
    Get the home directory of a user.

    Returns: path to the user's home directory
    """
    check_account_status(username)
    account_data = ldap_connection.user_lookup(username)
    return account_data['homeDirectory'][0]


def update_home(username, home):
    """
    Set the home directory of a user.

    Parameters:
        username - the UNIX account username
        home     - new home directory for the user
    """
    check_account_status(username)
    if not home[0] == '/':
        raise InvalidArgument('home', home, 'relative path')
    account_data = ldap_connection.user_lookup(username)
    account_data['homeDirectory'] = [ home ]
    ldap_connection.user_modify(username, account_data)



### General Group Management ###

def create_group(groupname, minimum_id=None, maximum_id=None, description=''):
    """
    Creates a UNIX group. This involves adding an entry to LDAP.

    The UID/GID namespace may be divided into ranges according to group
    type or purpose. This function accept such a range to allocate ids from.
    If none is specified, it will use the default from the configuration file.

    If a group needs directory accounts as members, or if the group will
    own files on NFS, you must add it to the directory with this function.

    If a group is relevant to only a single system and does not need any
    directory accounts as members, create it with the addgroup(8) utility
    for just that system instead.

    If you do not specify description, the default will be used. If no
    description at all is wanted, set description to None.

    Parameters:
        groupname   - UNIX group name
        minimum_id  - the smallest GID to assign
        maximum_id  - the largest GID to assign
        description - description LDAP attribute

    Exceptions:
        NoAvailableIDs - when the ID range is exhausted
        GroupException - when not connected
        LDAPException  - on LDAP failure

    Returns: the gid number of the new group

    Example: create_group('ninjas', 10000, 14999)
    """

    # check connection
    if not connected():
        raise AccountException("Not connected to LDAP and Kerberos")

    # check groupname format
    if not groupname or not re.match(cfg['groupname_regex'], groupname):
        raise InvalidArgument("groupname", groupname, "expected format %s" % repr(cfg['groupname_regex']))

    # load defaults for unspecified parameters
    if not minimum_id and maximum_id:
        minimum_id = cfg['group_min_id']
        maximum_id = cfg['group_max_id']
    if description == '':
        description = cfg['group_desc']

    check_name_usage(groupname)

    # determine the first available groupid
    groupid = first_available_id(cfg['group_min_id'], cfg['group_max_id'])
    if not groupid:
        raise NoAvailableIDs(minimum_id, maximum_id)

    ### Group creation ###

    # create the LDAP entry
    ldap_connection.group_add(groupname, groupid, description)

    return groupid


def delete_group(groupname):
    """
    Deletes a group.     

    Returns: the deleted LDAP information
    """

    # check connection
    if not connected():
        raise AccountException("Not connected to LDAP")

    # get account state 
    ldap_state = ldap_connection.group_lookup(groupname)

    # fail if no data is found in either LDAP or Kerberos
    if not ldap_state:
        raise NoSuchGroup(groupname, "LDAP")

    ### Group deletion ###

    # delete the LDAP entry
    if ldap_state:
        ldap_connection.group_delete(groupname)

    return ldap_state


def check_membership(username, groupname):
    """
    Determines whether an account is a member of a group
    by checking the group's member list and the user's
    default group.

    Returns: True if username is a member of groupname
    """

    check_account_status(username)
    check_group_status(groupname)

    group_data = ldap_connection.group_lookup(groupname)
    user_data = ldap_connection.user_lookup(username)

    group_members = get_members(groupname, group_data)
    group_id = int(group_data['gidNumber'][0])
    user_group = int(user_data['gidNumber'][0])

    return username in group_members or group_id == user_group
    

def get_members(groupname, group_data=None):
    """
    Retrieve a list of members of a group. This list
    will not include accounts that are members because
    their gidNumber attribute matches the group's.

    Parameters:
        group_data - result of a previous LDAP lookup on groupname (internal)

    Returns: a list of usernames
    """

    check_group_status(groupname)

    if not group_data:
        group_data = ldap_connection.group_lookup(groupname)

    if 'memberUid' in group_data:
        group_members = group_data['memberUid']
    else:
        group_members = []

    return group_members

    
def add_member(username, groupname):
    """
    Add an account to the list of group members.

    Returns: False if the user was already a member, else True
    """

    check_account_status(username)
    check_group_status(groupname)

    group_data = ldap_connection.group_lookup(groupname)
    group_members = get_members(groupname, group_data)

    if groupname in group_members:
        return False
    
    group_members.append(username)
    group_data['memberUid'] = group_members
    ldap_connection.group_modify(groupname, group_data)

    return True


def remove_member(username, groupname):
    """
    Removes an account from the list of group members.

    Returns: True if the user was a member, else False
    """

    check_account_status(username)
    check_group_status(groupname)

    group_data = ldap_connection.group_lookup(groupname)
    group_members = get_members(groupname, group_data)

    if username not in group_members:
        return False

    while username in group_members:
        group_members.remove(username)

    group_data['memberUid'] = group_members
    ldap_connection.group_modify(groupname, group_data)

    return True


### Account Types ###

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

    # check connection
    if not connected():
        raise AccountException("not connected to LDAP and Kerberos")

    # check username format
    if not username or not re.match(cfg['username_regex'], username):
        raise InvalidArgument("username", username, "expected format %s" % repr(cfg['username_regex']))

    # check password length
    if not password or len(password) < cfg['min_password_length']:
        raise InvalidArgument("password", "<hidden>", "too short (minimum %d characters)" % cfg['min_password_length'])

    args = [ "/usr/bin/addmember", "--stdin", username, name, program ]
    addmember = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = addmember.communicate(password)
    status = addmember.wait()

    if status:
        raise ChildFailed("addmember", status, out+err)


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

    # check connection
    if not connected():
        raise AccountException("not connected to LDAP and Kerberos")

    # check username format
    if not username or not re.match(cfg['username_regex'], username):
        raise InvalidArgument("username", username, "expected format %s" % repr(cfg['username_regex']))
    
    args = [ "/usr/bin/addclub", username, name ]
    addclub = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = addclub.communicate()
    status = addclub.wait()

    if status:
        raise ChildFailed("addclub", status, out+err)


def create_adm(username, name):
    """
    Creates a UNIX user account with options tailored to long-lived
    administrative accounts (e.g. vp, www, sysadmin, etc). 

    Parameters:
        username - the desired UNIX username
        name     - a descriptive name or purpose

    Exceptions:
        InvalidArgument - on bad account attributes provided

    Returns: the uid number of the new account

    See: create()
    """

    # check connection
    if not connected():
        raise AccountException("not connected to LDAP and Kerberos")

    # check username format
    if not username or not re.match(cfg['username_regex'], username):
        raise InvalidArgument("username", username, "expected format %s" % repr(cfg['username_regex']))

    password = None
    minimum_id = cfg['admin_min_id']
    maximum_id = cfg['admin_max_id']
    home = cfg['admin_home'] + '/' + username
    description = cfg['admin_desc']
    gecos_field = build_gecos(name)
    shell = cfg['admin_shell']
    group = cfg['admin_group']

    return create(username, name, minimum_id, maximum_id, home, password, description, gecos_field, shell, group)



### Miscellaneous Helpers ###

def check_name_usage(name):
    """
    Helper function: Ensures a user or group name does not exist in either
    Kerberos, LDAP, or through calls to libc and NSS. This is used prior to
    creating an accout or group to determine if the name is free.

    Parameters:
        name - the user or group name to check for

    Exceptions:
        NameConflict - if the name was found anywhere
    """

    # see if user exists in LDAP
    if ldap_connection.account_lookup(name):
        raise NameConflict(name, "account", "LDAP")

    # see if group exists in LDAP
    if ldap_connection.group_lookup(name):
        raise NameConflict(name, "group", "LDAP")

    # see if user exists in Kerberos
    principal = name + '@' + cfg['realm']
    if krb_connection.get_principal(principal):
        raise NameConflict(name, "account", "KRB")

    # see if user exists by getpwnam(3)
    try:
        pwd.getpwnam(name)
        raise NameConflict(name, "account", "NSS")
    except KeyError:
        pass

    # see if group exists by getgrnam(3)
    try:
        grp.getgrnam(name)
        raise NameConflict(name, "group", "NSS")
    except KeyError:
        pass


def check_account_status(username, require_ldap=True, require_krb=False):
    """Helper function to verify that an account exists."""

    if not connected():
        raise AccountException("Not connected to LDAP and Kerberos")
    if require_ldap and not ldap_connection.account_lookup(username):
        raise NoSuchAccount(username, "LDAP")
    if require_krb and not krb_connection.get_principal(username):
        raise NoSuchAccount(username, "KRB")


def check_group_status(groupname):
    """Helper function to verify that a group exists."""
    
    if not connected(): 
        raise AccountException("Not connected to LDAP and Kerberos")
    if not ldap_connection.group_lookup(groupname):
        raise NoSuchGroup(groupname, "LDAP")


def parse_gecos(gecos_data):
    """
    Build a dictionary out of a chfn(1) style GECOS string.

    Parameters:
        gecos_data - a gecos string formatted by chfn(1)

    Returns: a dictinoary of components
    
    Example: parse_gecos('Michael Spang,,,') -> {
                 'fullname': 'Michael Spang',
                 'roomnumber': '',
                 'workphone': '',
                 'homephone': '',
                 'other': None
             }
    """
    
    # silently remove erroneous colons
    while ':' in gecos_data:
        index = gecos_data.find(':')
        gecos_data = gecos_data[:index] + gecos_data[index+1:]

    gecos_vals = gecos_data.split(',', 4)
    gecos_vals.extend([ None ] * (5-len(gecos_vals)))
    gecos_keys = ['fullname', 'roomnumber', 'workphone',
                  'homephone', 'other' ]
    return dict((gecos_keys[i], gecos_vals[i]) for i in xrange(5))


def build_gecos(fullname=None, roomnumber=None, workphone=None, homephone=None, other=None):
    """
    Build a chfn(1)-style GECOS field from its components.

    See: chfn(1)
    
    Parameters:
        fullname   - GECOS full name
        roomnumber - GECOS room number
        workphone  - GECOS work phone
        homephone  - GECOS home phone
        other      - GECOS other

    Returns: string appropriate for a GECOS field value
    """

    # check first four params for illegal chars
    args = (fullname, roomnumber, workphone, homephone)
    names = ('fullname', 'roomnumber', 'workphone', 'homephone')
    for index in xrange(4):
        for badchar in (',', ':', '='):
            if args[index] and badchar in str(args[index]):
                raise InvalidArgument(names[index], args[index], "invalid characters")

    # check other for illegal chars
    if other and ':' in str(other):
        raise InvalidArgument('other', other, "invalid characters")
    
    # join the fields
    if fullname is not None:
        gecos_data = str(fullname)
    fields = [ fullname, roomnumber, workphone, homephone, other ]
    for idx in xrange(len(fields), 0, -1):
        if not fields[idx-1]:
            fields.pop()
        else:
            break
    while None in fields:
        fields[fields.index(None)] = ''
    return ','.join(map(str, fields))


def check_id_nss(ugid):
    """Helper to ensure there is no account or group with an ID."""

    try:
        pwd.getpwuid(ugid)
        return False
    except KeyError:
        pass

    try:
        grp.getgrgid(ugid)
        return False
    except KeyError:
        pass

    return True


def first_available_id(minimum, maximum):
    """
    Determines the first available id within a range.

    To be "available", there must be neither a user
    with the id nor a group with the id.

    Parameters:
        minimum - smallest id that may be returned
        maximum - largest id that may be returned

    Returns: the id, or None if there are none available

    Example: first_available_id(20000, 40000) -> 20018
    """

    # get lists of used uids and gids in LDAP
    uids = ldap_connection.used_uids(minimum, maximum)
    gids = ldap_connection.used_gids(minimum, maximum)

    # iterate through the lists and return the first available
    for ugid in xrange(minimum, maximum+1):
        if ugid not in uids and ugid not in gids and check_id_nss(ugid):
            return ugid

    # no id found within the range
    return None



### Tests ###

if __name__ == '__main__':

    import random
    from csc.common.test import *

    def test_exists(name):
        return ldap_connection.user_lookup(name) is not None, \
            ldap_connection.group_lookup(name) is not None, \
            krb_connection.get_principal(name) is not None

    # t=test u=user m=member a=adminv c=club
    # g=group r=real e=expected n=new
    tuname = 'testuser'
    turname = 'Test User'
    tunrname = 'User Test'
    tudesc = 'May be deleted'
    tuhome = '/home/testuser'
    tunhome = '/users/testuser'
    tushell = '/bin/false'
    tunshell = '/bin/true'
    tugecos = 'Test User,,,'
    tungecos = 'User Test,,,'
    tmname = 'testmember'
    tmrname = 'Test Member'
    tmmid = 31415
    tcname = 'testclub'
    tcrname = 'Test Club'
    tcmid = 98696
    taname = 'testadm'
    tarname = 'Test Adm' 
    tgname = 'testgroup'
    tgdesc = 'Test Group'
    minid = 99999000
    maxid = 100000000
    tpw = str(random.randint(10**30, 10**31-1))
    tgecos = 'a,b,c,d,e'
    tgecos_args = 'a','b','c','d','e'

    test(connect)
    connect()
    success()

    try:
        delete(tuname); delete(tmname)
        delete(tcname); delete(taname)
        delete_group(tgname)
    except (NoSuchAccount, NoSuchGroup):
        pass

    test(create)
    create(tuname, turname, minid, maxid, tuhome, tpw, tudesc, tugecos, tushell)
    exists = test_exists(tuname)
    expected = (True, True, True)
    assert_equal(expected, exists)
    success()

    test(create_member)
    create_member(tmname, tpw, tmrname, tmmid)
    exists = test_exists(tmname)
    expected = (True, False, True)
    assert_equal(expected, exists)
    success()

    test(create_club)
    create_club(tcname, tmrname, tmmid)
    exists = test_exists(tcname)
    expected = (True, False, False)
    assert_equal(expected, exists)
    success()

    test(create_adm)
    create_adm(taname, tarname)
    exists = test_exists(taname)
    expected = (True, False, False)
    assert_equal(expected, exists)
    success()

    test(create_group)
    create_group(tgname, minid, maxid, tgdesc)
    exists = test_exists(tgname)
    expected = (False, True, False)
    assert_equal(expected, exists)
    success()

    test(status)
    assert_equal((True, True), status(tmname))
    assert_equal((True, False), status(tcname))
    success()

    test(reset_password)
    reset_password(tuname, str(int(tpw)/2))
    reset_password(tmname, str(int(tpw)/3))
    negative(reset_password, (tcname,str(int(tpw)/4)), NoSuchAccount, "club should not have password")
    negative(reset_password, (taname,str(int(tpw)/5)), NoSuchAccount, "club should not have password")
    success()

    test(get_uid)
    tuuid = get_uid(tuname)
    assert_equal(True, int(tuuid) >= 0)
    success()

    test(get_gid)
    tugid = get_gid(tuname)
    assert_equal(True, int(tugid) >= 0)
    success()

    test(get_gecos)
    ugecos = get_gecos(tuname)
    assert_equal(tugecos, ugecos)
    success()

    test(update_gecos)
    update_gecos(tuname, tungecos)
    ugecos = get_gecos(tuname)
    assert_equal(tungecos, ugecos)
    success()

    test(get_shell)
    ushell = get_shell(tuname)
    assert_equal(tushell, ushell)
    success()

    test(update_shell)
    update_shell(tuname, tunshell, False)
    ushell = get_shell(tuname)
    assert_equal(ushell, tunshell)
    success()

    test(get_name)
    urname = get_name(tuname)
    assert_equal(turname, urname)
    success()

    test(update_name)
    update_name(tuname, tunrname)
    urname = get_name(tuname)
    assert_equal(urname, tunrname)
    success()

    test(get_home)
    uhome = get_home(tuname)
    assert_equal(tuhome, uhome)
    success()

    test(update_home)
    update_home(tuname, tunhome)
    urhome = get_home(tuname)
    assert_equal(urhome, tunhome)
    success()

    test(get_members)
    members = get_members(tgname)
    expected = []
    assert_equal(expected, members)
    success()

    test(check_membership)
    member = check_membership(tuname, tgname)
    assert_equal(False, member)
    member = check_membership(tuname, tuname)
    assert_equal(True, member)
    success()

    test(add_member)
    add_member(tuname, tgname)
    assert_equal(True, check_membership(tuname, tgname))
    assert_equal([tuname], get_members(tgname))
    success()

    test(remove_member)
    assert_equal(True, remove_member(tuname, tgname))
    assert_equal(False, check_membership(tuname, tgname))
    assert_equal(False, remove_member(tuname, tgname))
    success()

    test(build_gecos)
    assert_equal(tgecos, build_gecos(*tgecos_args))
    success()

    test(parse_gecos)
    gecos_dict = parse_gecos(tgecos)
    assert_equal(tgecos, build_gecos(**gecos_dict))
    success()

    test(delete)
    delete(tuname)
    exists = test_exists(tuname)
    expected = (False, False, False)
    assert_equal(expected, exists)
    delete(tmname)
    exists = test_exists(tmname)
    assert_equal(expected, exists)
    delete(tcname)
    exists = test_exists(tcname)
    assert_equal(expected, exists)
    delete(taname)
    exists = test_exists(taname)
    assert_equal(expected, exists)
    success()

    test(delete_group)
    delete_group(tgname)
    exists = test_exists(tgname)
    expected = (False, False, False)
    assert_equal(expected, exists)
    success()

    test(disconnect)
    disconnect()
    success()
