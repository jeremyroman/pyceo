"""
UNIX Accounts Administration

This module contains functions for creating, deleting, and manipulating
UNIX user accounts and account groups in the CSC LDAP directory.
"""
import re, pwd, grp, os, subprocess
from csc.common import conf
from csc.common.excep import InvalidArgument
from csc.backends import ldapi


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

LDAPException = ldapi.LDAPException
ConfigurationException = conf.ConfigurationException

class AccountException(Exception):
    """Base exception class for account-related errors."""

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

def connect():
    """Connect to LDAP and Kerberos and load configuration. You must call before anything else."""

    configure()

    # connect to the LDAP server
    ldap_connection.connect_sasl(cfg['server_url'], cfg['sasl_mech'],
        cfg['sasl_realm'], cfg['admin_bind_userid'],
        ('keytab', cfg['admin_bind_keytab']), cfg['users_base'],
        cfg['groups_base'])


def disconnect():
    """Disconnect from LDAP and Kerberos. Call this before quitting."""

    ldap_connection.disconnect()


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

    # check username format
    if not username or not re.match(cfg['username_regex'], username):
        raise InvalidArgument("username", username, "expected format %s" % repr(cfg['username_regex']))
    
    args = [ "/usr/bin/addclub", username, name ]
    addclub = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = addclub.communicate()
    status = addclub.wait()

    if status:
        raise ChildFailed("addclub", status, out+err)
