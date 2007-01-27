# $Id: accounts.py 44 2006-12-31 07:09:27Z mspang $
# UNIX Accounts Module
import re
from csc.backend import ldapi, krb
from csc.lib import read_config

CONFIG_FILE = '/etc/csc/accounts.cf'

cfg = {}

# error constants
SUCCESS = 0
LDAP_EXISTS = 1
LDAP_NO_IDS = 2
LDAP_NO_USER = 3
KRB_EXISTS = 5
KRB_NO_USER = 6
BAD_USERNAME = 8
BAD_REALNAME = 9

# error messages
errors = [ "Success", "LDAP: entry exists",
    "LDAP: no user ids available", "LDAP: no such entry",
    "KRB: principal exists", "KRB: no such principal",
    "Invalid username", "Invalid real name"]


class AccountException(Exception):
    """Exception class for account-related errors."""


def load_configuration():
    """Load Accounts Configuration."""
    
    # configuration already loaded?
    if len(cfg) > 0:
        return
    
    # read in the file
    cfg_tmp = read_config(CONFIG_FILE)

    if not cfg_tmp:
        raise AccountException("unable to read configuration file: %s" % CONFIG_FILE)

    # check that essential fields are completed
    mandatory_fields = [ 'minimum_id', 'maximum_id', 'shell', 'home',
        'gid', 'server_url', 'users_base', 'groups_base', 'bind_dn',
        'bind_password', 'realm', 'principal', 'keytab', 'username_regex',
        'realname_regex'
    ]

    for field in mandatory_fields:
        if not field in cfg_tmp:
            raise AccountException("missing configuration option: %s" % field)
        if not cfg_tmp[field]:
            raise AccountException("null configuration option: %s" % field)
    
    # check that numeric fields are ints
    numeric_fields = [ 'minimum_id', 'maximum_id', 'gid' ]

    for field in numeric_fields:
        if not type(cfg_tmp[field]) in (int, long):
            raise AccountException("non-numeric value for configuration option: %s" % field)

    # update the current configuration with the loaded values
    cfg.update(cfg_tmp)
        

def create_account(username, password, realname='', gecos_other=''):
    """
    Creates a UNIX account for a member. This involves
    first creating a directory entry, then creating
    a Kerberos principal.

    Parameters:
        username - UNIX username for the member
        realname - real name of the member
        password - password for the account

    Exceptions:
        LDAPException - on LDAP failure
        KrbException  - on Kerberos failure
        
    Returns:
        SUCCESS      - on success
        BAD_REALNAME - on badly formed real name
        BAD_USERNAME - on badly formed user name
        LDAP_EXISTS  - when the user exists in LDAP
        LDAP_NO_IDS  - when no user ids are free
        KRB_EXISTS   - when the user exists in Kerberos
    """

    # Load Configuration
    load_configuration()

    ### Connect to the Backends ###

    ldap_connection = ldapi.LDAPConnection()
    krb_connection = krb.KrbConnection()

    try:

        # connect to the LDAP server
        ldap_connection.connect(cfg['server_url'], cfg['bind_dn'], cfg['bind_password'], cfg['users_base'], cfg['groups_base'])

        # connect to the Kerberos master server
        krb_connection.connect(cfg['principal'], cfg['keytab'])

        ### Sanity-checks ###
   
        # check the username and realame for validity
        if not re.match(cfg['username_regex'], username):
            return BAD_USERNAME
        if not re.match(cfg['realname_regex'], realname):
            return BAD_REALNAME

        # see if user exists in LDAP
        if ldap_connection.user_lookup(username):
            return LDAP_EXISTS

        # determine the first available userid
        userid = ldap_connection.first_id(cfg['minimum_id'], cfg['maximum_id'])
        if not userid: return LDAP_NO_IDS

        # build principal name from username
        principal = username + '@' + cfg['realm']
    
        # see if user exists in Kerberos
        if krb_connection.get_principal(principal):
            return KRB_EXISTS
    
        ### User creation ###

        # process gecos_other (used to store memberid)
        if gecos_other:
            gecos_other = ',' + str(gecos_other)
    
        # account information defaults
        shell = cfg['shell']
        home = cfg['home'] + '/' + username
        gecos = realname + ',,,' + gecos_other
        gid = cfg['gid']
    
        # create the LDAP entry
        ldap_connection.user_add(username, realname, shell, userid, gid, home, gecos)
    
        # create the Kerberos principal
        krb_connection.add_principal(principal, password)

    finally:
        ldap_connection.disconnect()
        krb_connection.disconnect()
    
    return SUCCESS
    

def delete_account(username):
    """
    Deletes the UNIX account of a member.
    
    Parameters:
        username - UNIX username for the member

    Exceptions:
        LDAPException - on LDAP failure
        KrbException  - on Kerberos failure
        
    Returns:
        SUCCESS      - on success
        LDAP_NO_USER - when the user does not exist in LDAP
        KRB_NO_USER  - when the user does not exist in Kerberos
    """

    # Load Configuration
    load_configuration()

    ### Connect to the Backends ###

    ldap_connection = ldapi.LDAPConnection()
    krb_connection = krb.KrbConnection()

    try:
    
        # connect to the LDAP server
        ldap_connection.connect(cfg['server_url'], cfg['bind_dn'], cfg['bind_password'], cfg['users_base'], cfg['groups_base'])

        # connect to the Kerberos master server
        krb_connection.connect(cfg['principal'], cfg['keytab'])

        ### Sanity-checks ###
    
        # ensure user exists in LDAP
        if not ldap_connection.user_lookup(username):
            return LDAP_NO_USER
    
        # build principal name from username
        principal = username + '@' + cfg['realm']

        # see if user exists in Kerberos
        if not krb_connection.get_principal(principal):
            return KRB_NO_USER

        ### User deletion ###
    
        # delete the LDAP entry
        ldap_connection.user_delete(username)
    
        # delete the Kerberos principal
        krb_connection.delete_principal(principal)

    finally:
        ldap_connection.disconnect()
        krb_connection.disconnect()
    
    return SUCCESS



### Tests ###

if __name__ == '__main__':

    # A word of notice: this test creates a _working_ account (and then deletes it).
    # If deletion fails it must be cleaned up manually.
    
    # a bit of salt so the test account is reasonably tough to crack
    import random
    pw = str(random.randint(100000000000000000, 999999999999999999))
    
    print "running create_account('testuser', ..., 'Test User', ...)", "->", errors[create_account('testuser', pw, 'Test User')]
    print "running delete_account('testuser')", "->", errors[delete_account('testuser')]

