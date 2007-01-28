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

        if bind_pw is None: bind_pw = ''

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

        return self.ldap is not None



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
            uid - the UNIX username to look up

        Returns: attributes of user with uid

        Example: connection.user_lookup('mspang') ->
                     { 'uid': 'mspang', 'uidNumber': 21292 ...}
        """

        if not self.connected(): raise LDAPException("Not connected!")
        
        dn = 'uid=' + uid + ',' + self.user_base
        return self.lookup(dn)
        

    def user_search(self, search_filter):
        """
        Helper for user searches.

        Parameters:
            search_filter - LDAP filter string to match users against

        Returns: the list of uids matched (usernames)
        """

        # search for entries that match the filter
        try:
            matches = self.ldap.search_s(self.user_base, ldap.SCOPE_SUBTREE, search_filter)
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

        Returns: the list of uids matched (usernames)

        Example: connection.user_search_id(21292) -> ['mspang']
        """

        # search for posixAccount entries with the specified uidNumber
        search_filter = '(&(objectClass=posixAccount)(uidNumber=%d))' % uidNumber
        return self.user_search(search_filter)


    def user_search_gid(self, gidNumber):
        """
        Retrieves a list of users with a certain UNIX gid
        number (search by default group).

        Returns: the list of uids matched (usernames)
        """

        # search for posixAccount entries with the specified gidNumber
        search_filter = '(&(objectClass=posixAccount)(gidNumber=%d))' % gidNumber
        return self.user_search(search_filter)


    def user_add(self, uid, cn, uidNumber, gidNumber, homeDirectory, loginShell=None, gecos=None, description=None):
        """
        Adds a user to the directory.

        Parameters:
            uid           - the UNIX username for the account
            cn            - the real name of the member
            uidNumber     - the UNIX user id number
            gidNumber     - the UNIX group id number (default group)
            homeDirectory - home directory for the user
            loginShell    - login shell for the user
            gecos         - comment field (usually stores name etc)
            description   - description field (optional and unimportant)

        Example: connection.user_add('mspang', 'Michael Spang',
                     21292, 100, '/users/mspang', '/bin/bash', 
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
        
        if loginShell:
            attrs['loginShell'] = loginShell
        if description:
            attrs['description'] = [ description ]

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
            attrs - dictionary as returned by user_lookup() with changes to make.
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

        Returns: attributes of the group's LDAP entry

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
        
        Returns: a list of groups with gid gidNumber

        Example: connection.group_search_id(1001) -> ['office']
        """

        # search for posixAccount entries with the specified uidNumber
        try:
            search_filter = '(&(objectClass=posixGroup)(gidNumber=%d))' % gidNumber
            matches = self.ldap.search_s(self.group_base, ldap.SCOPE_SUBTREE, search_filter)
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


    def group_add(self, cn, gidNumber, description=None):
        """
        Adds a group to the directory.

        Example: connection.group_add('office', 1001, 'Office Staff')
        """
        
        dn = 'cn=' + cn + ',' + self.group_base
        attrs = {
            'objectClass': [ 'top', 'posixGroup' ],
            'cn': [ cn ],
            'gidNumber': [ str(gidNumber) ],
        }
        if description:
            attrs['description'] = description

        try:
            modlist = ldap.modlist.addModlist(attrs)
            self.ldap.add_s(dn, modlist)
        except ldap.LDAPError, e:
            raise LDAPException("unable to add group: %s" % e)


    def group_modify(self, cn, attrs):
        """
        Update group attributes in the directory.
        
        The only available updates are fairly destructive (rename or renumber)
        but this method is provided for completeness.

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

        Example: connection.group_delete('office')
        """
        
        try:
            dn = 'cn=' + cn + ',' + self.group_base
            self.ldap.delete_s(dn)
        except ldap.LDAPError, e:
            raise LDAPException("unable to delete group: %s" % e)


    ### Miscellaneous Methods ###

    def used_uids(self, minimum=None, maximum=None):
        """
        Compiles a list of used UIDs in a range.

        Parameters:
            minimum - smallest uid to return in the list
            maximum - largest uid to return in the list

        Returns: list of integer uids

        Example: connection.used_uids(20000, 40000) -> [20000, 20001, ...]
        """

        try:
            users = self.ldap.search_s(self.user_base, ldap.SCOPE_SUBTREE, '(objectClass=posixAccount)', ['uidNumber'])
        except ldap.LDAPError, e:
            raise LDAPException("search for uids failed: %s" % e)
        
        uids = []
        for user in users:
            dn, attrs = user
            uid = int(attrs['uidNumber'][0])
            if (not minimum or uid >= minimum) and (not maximum or uid <= maximum):
                uids.append(uid)

        return uids
            
    
    def used_gids(self, minimum=None, maximum=None):
        """
        Compiles a list of used GIDs in a range.

        Parameters:
            minimum - smallest gid to return in the list
            maximum - largest gid to return in the list

        Returns: list of integer gids

        Example: connection.used_gids(20000, 40000) -> [20000, 20001, ...]
        """

        try:
            users = self.ldap.search_s(self.user_base, ldap.SCOPE_SUBTREE, '(objectClass=posixAccount)', ['gidNumber'])
        except ldap.LDAPError, e:
            raise LDAPException("search for gids failed: %s" % e)
        
        gids = []
        for user in users:
            dn, attrs = user
            gid = int(attrs['gidNumber'][0])
            if (not minimum or gid >= minimum) and (not maximum or gid <= maximum):
                gids.append(gid)

        return gids



### Tests ###

if __name__ == '__main__':
    
    from csc.common.test import *

    conffile = '/etc/csc/ldap.cf'
    cfg = dict([map(str.strip, a.split("=", 1)) for a in map(str.strip, open(conffile).read().split("\n")) if "=" in a ]) 
    srvurl = cfg['server_url'][1:-1]
    binddn = cfg['admin_bind_dn'][1:-1]
    bindpw = cfg['admin_bind_pw'][1:-1]
    ubase = cfg['users_base'][1:-1]
    gbase = cfg['groups_base'][1:-1]
    minid = 99999000
    maxid = 100000000

    # t=test u=user g=group c=changed r=real e=expected
    tuname = 'testuser'
    turname = 'Test User'
    tuhome = '/home/testuser'
    tushell = '/bin/false'
    tugecos = 'Test User,,,'
    tgname = 'testgroup'
    cushell = '/bin/true'
    cuhome = '/home/changed'
    curname = 'Test Modified User'

    test("LDAPConnection()")
    connection = LDAPConnection()
    success()

    test("disconnect()")
    connection.disconnect()
    success()

    test("connect()")
    connection.connect(srvurl, binddn, bindpw, ubase, gbase)
    if not connection.connected():
        fail("not connected")
    success()

    try:
        connection.user_delete(tuname)
        connection.group_delete(tgname)
    except LDAPException:
        pass

    test("used_uids()")
    uids = connection.used_uids(minid, maxid)
    if type(uids) is not list:
        fail("list not returned")
    success()

    test("used_gids()")
    gids = connection.used_gids(minid, maxid)
    if type(gids) is not list:
        fail("list not returned")
    success()

    unusedids = []
    for idnum in xrange(minid, maxid):
        if not idnum in uids and not idnum in gids:
            unusedids.append(idnum)

    tuuid = unusedids.pop()
    tugid = unusedids.pop()
    eudata = {
            'uid': [ tuname ],
            'loginShell': [ tushell ],
            'uidNumber': [ str(tuuid) ],
            'gidNumber': [ str(tugid) ],
            'gecos': [ tugecos ],
            'homeDirectory': [ tuhome ],
            'cn': [ turname ]
            }

    test("user_add()")
    connection.user_add(tuname, turname, tuuid, tugid, tuhome, tushell, tugecos)
    success()

    tggid = unusedids.pop()
    egdata = {
            'cn': [ tgname ],
            'gidNumber': [ str(tggid) ]
            }

    test("group_add()")
    connection.group_add(tgname, tggid)
    success()

    test("user_lookup()")
    udata = connection.user_lookup(tuname)
    del udata['objectClass']
    assert_equal(eudata, udata)
    success()

    test("group_lookup()")
    gdata = connection.group_lookup(tgname)
    del gdata['objectClass']
    assert_equal(egdata, gdata)
    success()

    test("user_search_id()")
    eulist = [ tuname ]
    ulist = connection.user_search_id(tuuid)
    assert_equal(eulist, ulist)
    success()

    test("user_search_gid()")
    ulist = connection.user_search_gid(tugid)
    if tuname not in ulist:
        fail("(%s) not in (%s)" % (tuname, ulist))
    success()

    ecudata = connection.user_lookup(tuname)
    ecudata['loginShell'] = [ cushell ]
    ecudata['homeDirectory'] = [ cuhome ]
    ecudata['cn'] = [ curname ]

    test("user_modify")
    connection.user_modify(tuname, ecudata)
    cudata = connection.user_lookup(tuname)
    assert_equal(ecudata, cudata)
    success()

    ecgdata = connection.group_lookup(tgname)
    ecgdata['memberUid'] = [ tuname ]

    test("group_modify()")
    connection.group_modify(tgname, ecgdata)
    cgdata = connection.group_lookup(tgname)
    assert_equal(ecgdata, cgdata)
    success()

    test("user_delete()")
    connection.group_delete(tgname)
    success()

    test("disconnect()")
    connection.disconnect()
    success()
