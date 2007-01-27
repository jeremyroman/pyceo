# $Id: ldapi.py 41 2006-12-29 04:22:31Z mspang $
"""
LDAP Backend Interface

This module is intended to be a thin wrapper around LDAP operations.
Methods on the connection object correspond in a straightforward way
to LDAP queries and updates.

A LDAP entry is the most important component of a CSC UNIX account.
The entry contains the username, user id number, real name, shell,
and other important information. All non-local UNIX accounts must
have an LDAP entry, even if the account does not log in directly.

This module makes use of python-ldap, a Python module with bindings
to libldap, OpenLDAP's native C client library.
"""
import ldap.modlist


class LDAPException(Exception):
    """Exception class for LDAP-related errors."""


class LDAPConnection(object):
    """
    Connection to the LDAP directory. All directory
    queries and updates are made via this class.

    Exceptions: (all methods)
        LDAPException - on directory query failure

    Example:
         connection = LDAPConnection()
         connection.connect(...)

         # make queries and updates, e.g.
         connection.user_delete('mspang')

         connection.disconnect()
    """

    def __init__(self):
        self.ldap = None

    
    def connect(self, server, bind_dn, bind_pw, user_base, group_base):
        """
        Establish a connection to the LDAP Server.

        Parameters:
            server     - connection string (e.g. ldap://foo.com, ldaps://bar.com)
            bind_dn    - distinguished name to bind to
            bind_pw    - password of bind_dn
            user_base  - base of the users subtree
            group_base - baes of the group subtree

        Example: connect('ldaps:///', 'cn=ceo,dc=csclub,dc=uwaterloo,dc=ca',
                     'secret', 'ou=People,dc=csclub,dc=uwaterloo,dc=ca',
                     'ou=Group,dc=csclub,dc=uwaterloo,dc=ca')
        
        """

        if bind_pw == None: bind_pw = ''

        try:

            # open the connection
            self.ldap = ldap.initialize(server)

            # authenticate as ceo
            self.ldap.simple_bind_s(bind_dn, bind_pw)

        except ldap.LDAPError, e:
            raise LDAPException("unable to connect: %s" % e)

        self.user_base = user_base
        self.group_base = group_base


    def disconnect(self):
        """Close the connection to the LDAP server."""
        
        if self.ldap:

            # close connection
            try:
                self.ldap.unbind_s()
                self.ldap = None
            except ldap.LDAPError, e:
                raise LDAPException("unable to disconnect: %s" % e)


    def connected(self):
        """Determine whether the connection has been established."""

        return self.ldap != None



    ### Helper Methods ###

    def lookup(self, dn):
        """
        Helper method to retrieve the attributes of an entry.

        Parameters:
            dn - the distinguished name of the directory entry

        Returns: a dictionary of attributes of the matched dn, or
                 None of the dn does not exist in the directory
        """

        # search for the specified dn
        try:
            matches = self.ldap.search_s(dn, ldap.SCOPE_BASE)
        except ldap.NO_SUCH_OBJECT:
            return None
        except ldap.LDAPError, e:
            raise LDAPException("unable to lookup dn %s: %s" % (dn, e))
            
        # this should never happen due to the nature of DNs
        if len(matches) > 1:
            raise LDAPException("duplicate dn in ldap: " + dn)
        
        # return the attributes of the single successful match
        else:
            match = matches[0]
            match_dn, match_attributes = match
            return match_attributes


    
    ### User-related Methods ###

    def user_lookup(self, uid):
        """
        Retrieve the attributes of a user.

        Parameters:
            uid - the UNIX user accound name of the user

        Returns: attributes of user with uid

        Example: connection.user_lookup('mspang') ->
                     { 'uid': 'mspang', 'uidNumber': 21292 ...}
        """
        
        dn = 'uid=' + uid + ',' + self.user_base
        return self.lookup(dn)
        

    def user_search(self, filter):
        """
        Helper for user searches.

        Parameters:
            filter - LDAP filter string to match users against

        Returns: the list of uids matched
        """

        # search for entries that match the filter
        try:
            matches = self.ldap.search_s(self.user_base, ldap.SCOPE_SUBTREE, filter)
        except ldap.LDAPError, e:
            raise LDAPException("user search failed: %s" % e)
        
        # list for uids found
        uids = []
        
        for match in matches:
            dn, attributes = match
            
            # uid is a required attribute of posixAccount
            if not attributes.has_key('uid'):
                raise LDAPException(dn + ' (posixAccount) has no uid')
            
            # do not handle the case of multiple usernames in one entry (yet)
            elif len(attributes['uid']) > 1:
                raise LDAPException(dn + ' (posixAccount) has multiple uids')
            
            # append the sole uid of this match to the list
            uids.append( attributes['uid'][0] )

        return uids


    def user_search_id(self, uidNumber):
        """
        Retrieves a list of users with a certain UNIX uid number.

        LDAP (or passwd for that matter) does not enforce any
        restriction on the number of accounts that can have
        a certain UID. Therefore this method returns a list of matches.

        Parameters:
            uidNumber - the user id of the accounts desired

        Returns: the list of uids matched

        Example: connection.user_search_id(21292) -> ['mspang']
        """

        # search for posixAccount entries with the specified uidNumber
        filter = '(&(objectClass=posixAccount)(uidNumber=%d))' % uidNumber
        return self.user_search(filter)


    def user_search_gid(self, gidNumber):
        """
        Retrieves a list of users with a certain UNIX gid number.

        Parameters:
            gidNumber - the group id of the accounts desired

        Returns: the list of uids matched
        """

        # search for posixAccount entries with the specified gidNumber
        filter = '(&(objectClass=posixAccount)(gidNumber=%d))' % gidNumber
        return self.user_search(filter)


    def user_add(self, uid, cn, loginShell, uidNumber, gidNumber, homeDirectory, gecos):
        """
        Adds a user to the directory.

        Parameters:
            uid           - the UNIX username for the account
            cn            - the full name of the member
            userPassword  - password of the account (our setup does not use this)
            loginShell    - login shell for the user
            uidNumber     - the UNIX user id number
            gidNumber     - the UNIX group id number
            homeDirectory - home directory for the user
            gecos         - comment field (usually stores miscellania)

        Example: connection.user_add('mspang', 'Michael Spang',
                     '/bin/bash', 21292, 100, '/users/mspang',
                     'Michael Spang,,,')
        """
        
        dn = 'uid=' + uid + ',' + self.user_base
        attrs = {
            'objectClass': [ 'top', 'account', 'posixAccount', 'shadowAccount' ],
            'uid': [ uid ],
            'cn': [ cn ],
            'loginShell': [ loginShell ],
            'uidNumber': [ str(uidNumber) ],
            'gidNumber': [ str(gidNumber) ],
            'homeDirectory': [ homeDirectory ],
            'gecos': [ gecos ],
        }

        try:
            modlist = ldap.modlist.addModlist(attrs)
            self.ldap.add_s(dn, modlist)
        except ldap.LDAPError, e:
            raise LDAPException("unable to add: %s" % e)


    def user_modify(self, uid, attrs):
        """
        Update user attributes in the directory.

        Parameters:
            uid   - username of the user to modify
            entry - dictionary as returned by user_lookup() with changes to make.
                    omitted attributes are DELETED.

        Example: user = user_lookup('mspang')
                 user['uidNumber'] = [ '0' ]
                 connection.user_modify('mspang', user)
        """

        # distinguished name of the entry to modify
        dn = 'uid=' + uid + ',' + self.user_base

        # retrieve current state of user
        old_user = self.user_lookup(uid)

        try:
            
            # build list of modifications to make
            changes = ldap.modlist.modifyModlist(old_user, attrs)

            # apply changes
            self.ldap.modify_s(dn, changes)

        except ldap.LDAPError, e:
            raise LDAPException("unable to modify: %s" % e)


    def user_delete(self, uid):
        """
        Removes a user from the directory.

        Parameters:
            uid - the UNIX username of the account
        
        Example: connection.user_delete('mspang')
        """
        
        try:
            dn = 'uid=' + uid + ',' + self.user_base
            self.ldap.delete_s(dn)
        except ldap.LDAPError, e:
            raise LDAPException("unable to delete: %s" % e)



    ### Group-related Methods ###

    def group_lookup(self, cn):
        """
        Retrieves the attributes of a group.

        Parameters:
            cn - the UNIX group name to lookup

        Returns: attributes of group with cn

        Example: connection.group_lookup('office') -> {
                     'cn': 'office',
                     'gidNumber', '1001',
                     ...
                 }
        """
        
        dn = 'cn=' + cn + ',' + self.group_base
        return self.lookup(dn)
                                                                                    

    def group_search_id(self, gidNumber):
        """
        Retrieves a list of groups with the specified UNIX group number.
        
        Parameters:
            gidNumber - the group id of the groups desired

        Returns: a list of groups with gid gidNumber

        Example: connection.group_search_id(1001) -> ['office']
        """

        # search for posixAccount entries with the specified uidNumber
        try:
            filter = '(&(objectClass=posixGroup)(gidNumber=%d))' % gidNumber
            matches = self.ldap.search_s(self.group_base, ldap.SCOPE_SUBTREE, filter)
        except ldap.LDAPError,e :
            raise LDAPException("group search failed: %s" % e)

        # list for groups found
        group_cns = []

        for match in matches:
            dn, attributes = match

            # cn is a required attribute of posixGroup
            if not attributes.has_key('cn'):
                raise LDAPException(dn + ' (posixGroup) has no cn')

            # do not handle the case of multiple cns for one group (yet)
            elif len(attributes['cn']) > 1:
                raise LDAPException(dn + ' (posixGroup) has multiple cns')

            # append the sole uid of this match to the list
            group_cns.append( attributes['cn'][0] )

        return group_cns


    def group_add(self, cn, gidNumber):
        """
        Adds a group to the directory.

        Parameters:
            cn        - the name of the group
            gidNumber - the number of the group

        Example: connection.group_add('office', 1001)
        """
        
        dn = 'cn=' + cn + ',' + self.group_base
        attrs = {
            'objectClass': [ 'top', 'posixGroup' ],
            'cn': [ cn ],
            'gidNumber': [ str(gidNumber) ],
        }

        try:
            modlist = ldap.modlist.addModlist(attrs)
            self.ldap.add_s(dn, modlist)
        except ldap.LDAPError, e:
            raise LDAPException("unable to add group: %s" % e)


    def group_modify(self, cn, attrs):
        """
        Update group attributes in the directory.
        
        The only available updates are fairly destructive
        (rename or renumber) but this method is provided
        for completeness.

        Parameters:
            cn    - name of the group to modify
            entry - dictionary as returned by group_lookup() with changes to make.
                    omitted attributes are DELETED.

        Example: group = group_lookup('office')
                 group['gidNumber'] = [ str(connection.first_id(20000, 40000)) ]
                 del group['memberUid']
                 connection.group_modify('office', group)
        """

        # distinguished name of the entry to modify
        dn = 'cn=' + cn + ',' + self.group_base

        # retrieve current state of group
        old_group = self.group_lookup(cn)

        try:
            
            # build list of modifications to make
            changes = ldap.modlist.modifyModlist(old_group, attrs)

            # apply changes
            self.ldap.modify_s(dn, changes)

        except ldap.LDAPError, e:
            raise LDAPException("unable to modify: %s" % e)


    def group_delete(self, cn):
        """
        Removes a group from the directory."

        Parameters:
            cn - the name of the group

        Example: connection.group_delete('office')
        """
        
        try:
            dn = 'cn=' + cn + ',' + self.group_base
            self.ldap.delete_s(dn)
        except ldap.LDAPError, e:
            raise LDAPException("unable to delete group: %s" % e)


    def group_members(self, cn):
        """
        Retrieves a group's members.

        Parameters:
            cn - the name of the group

        Example: connection.group_members('office') ->
                 ['sfflaw', 'jeperry', 'cschopf' ...]
        """

        group = self.group_lookup(cn)
        return group.get('memberUid', None)


    ### Miscellaneous Methods ###
    
    def first_id(self, minimum, maximum):
        """
        Determines the first available id within a range.

        To be "available", there must be neither a user
        with the id nor a group with the id.

        Parameters:
            minimum - smallest uid that may be returned
            maximum - largest uid that may be returned

        Returns: the id, or None if there are none available

        Example: connection.first_id(20000, 40000) -> 20018
        """

        # compile a list of used uids
        try:
            users = self.ldap.search_s(self.user_base, ldap.SCOPE_SUBTREE, '(objectClass=posixAccount)', ['uidNumber'])
        except ldap.LDAPError, e:
            raise LDAPException("search for uids failed: %s" % e)
        uids = []
        for user in users:
            dn, attrs = user
            uid = int(attrs['uidNumber'][0])
            if minimum <= uid <= maximum:
                uids.append(uid)

        # compile a list of used gids
        try:
            groups = self.ldap.search_s(self.group_base, ldap.SCOPE_SUBTREE, '(objectClass=posixGroup)', ['gidNumber'])
        except ldap.LDAPError, e:
            raise LDAPException("search for gids failed: %s" % e)
        gids = []
        for group in groups:
            dn, attrs = group
            gid = int(attrs['gidNumber'][0])
            if minimum <= gid <= maximum:
                gids.append(gid)

        # iterate through ids and return the first available
        for id in xrange(minimum, maximum+1):
            if not id in uids and not id in gids:
                return id

        # no suitable id was found
        return None


### Tests ###

if __name__ == '__main__':
    
    password_file = 'ldap.ceo'
    server   = 'ldaps:///'
    base_dn  = 'dc=csclub,dc=uwaterloo,dc=ca'
    bind_dn  = 'cn=ceo,' + base_dn
    user_dn  = 'ou=People,' + base_dn
    group_dn = 'ou=Group,' + base_dn
    bind_pw = open(password_file).readline().strip()

    connection = LDAPConnection()
    print "running disconnect()"
    connection.disconnect()
    print "running connect('%s', '%s', '%s', '%s', '%s')" % (server, bind_dn, '***', user_dn, group_dn)
    connection.connect(server, bind_dn, bind_pw, user_dn, group_dn)
    print "running user_lookup('mspang')", "->", "(%s)" % connection.user_lookup('mspang')['uidNumber'][0]
    print "running user_search_id(21292)", "->", connection.user_search_id(21292)
    print "running first_id(20000, 40000)", "->",
    first_id = connection.first_id(20000, 40000)
    print first_id
    print "running group_add('testgroup', %d)" % first_id
    try:
        connection.group_add('testgroup', first_id)
    except Exception, e:
        print "FAILED: %s (continuing)" % e
    print "running user_add('testuser', 'Test User', '/bin/false', %d, %d, '/home/null', 'Test User,,,')" % (first_id, first_id)
    try:
        connection.user_add('testuser', 'Test User', '/bin/false', first_id, first_id, '/home/null', 'Test User,,,')
    except Exception, e:
        print "FAILED: %s (continuing)" % e
    print "running user_lookup('testuser')", "->",
    user = connection.user_lookup('testuser')
    print repr(connection.user_lookup('testuser')['cn'][0])
    user['homeDirectory'] = ['/home/changed']
    user['loginShell'] = ['/bin/true']
    print "running user_modify(...)"
    connection.user_modify('testuser', user)
    print "running user_lookup('testuser')", "->",
    user = connection.user_lookup('testuser')
    print '(%s, %s)' % (user['homeDirectory'], user['loginShell'])
    print "running group_lookup('testgroup')", "->",
    group = connection.group_lookup('testgroup')
    print group
    print "running group_modify(...)"
    group['gidNumber'] = [str(connection.first_id(20000, 40000))]
    group['memberUid'] = [ str(first_id) ]
    connection.group_modify('testgroup', group)
    print "running group_lookup('testgroup')", "->",
    group = connection.group_lookup('testgroup')
    print group
    print "running user_delete('testuser')"
    connection.user_delete('testuser')
    print "running group_delete('testgroup')"
    connection.group_delete('testgroup')
    print "running user_search_gid(100)", "->", "[" + ", ".join(map(repr,connection.user_search_gid(100)[:10])) + " ...]"
    print "running group_members('office')", "->", "[" + ", ".join(map(repr,connection.group_members('office')[:10])) + " ...]"
    print "running disconnect()"
    connection.disconnect()
