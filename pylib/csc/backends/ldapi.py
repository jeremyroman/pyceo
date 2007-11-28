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
import ldap.modlist, ipc, os


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


    def connect_anon(self, uri, user_base, group_base):
        """
        Establish a connection to the LDAP Server.

        Parameters:
            uri        - connection string (e.g. ldap://foo.com, ldaps://bar.com)
            user_base  - base of the users subtree
            group_base - baes of the group subtree

        Example: connect('ldaps:///', 'cn=ceo,dc=csclub,dc=uwaterloo,dc=ca',
                     'secret', 'ou=People,dc=csclub,dc=uwaterloo,dc=ca',
                     'ou=Group,dc=csclub,dc=uwaterloo,dc=ca')

        """

        # open the connection
        self.ldap = ldap.initialize(uri)

        # authenticate
        self.ldap.simple_bind_s('', '')

        self.user_base = user_base
        self.group_base = group_base

    def connect_sasl(self, uri, bind_dn, mech, realm, userid, password, user_base, group_base):

        # open the connection
        self.ldap = ldap.initialize(uri)

        # authenticate
        sasl = Sasl(mech, realm, userid, password)
        self.ldap.sasl_interactive_bind_s(bind_dn, sasl)

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

    def lookup(self, dn, objectClass=None):
        """
        Helper method to retrieve the attributes of an entry.

        Parameters:
            dn - the distinguished name of the directory entry

        Returns: a dictionary of attributes of the matched dn, or
                 None of the dn does not exist in the directory
        """

        if not self.connected(): raise LDAPException("Not connected!")

        # search for the specified dn
        try:
            if objectClass:
                search_filter = '(objectClass=%s)' % self.escape(objectClass)
                matches = self.ldap.search_s(dn, ldap.SCOPE_BASE, search_filter)
            else:
                matches = self.ldap.search_s(dn, ldap.SCOPE_BASE)
        except ldap.NO_SUCH_OBJECT:
            return None
        except ldap.LDAPError, e:
            raise LDAPException("unable to lookup dn %s: %s" % (dn, e))
            
        # this should never happen due to the nature of DNs
        if len(matches) > 1:
            raise LDAPException("duplicate dn in ldap: " + dn)

        # dn was found, but didn't match the objectClass filter
        elif len(matches) < 1:
            return None

        # return the attributes of the single successful match
        match = matches[0]
        match_dn, match_attributes = match
        return match_attributes



    ### User-related Methods ###

    def user_lookup(self, uid, objectClass=None):
        """
        Retrieve the attributes of a user.

        Parameters:
            uid - the uid to look up

        Returns: attributes of user with uid
        """

        dn = 'uid=' + uid + ',' + self.user_base
        return self.lookup(dn, objectClass)


    def user_search(self, search_filter, params):
        """
        Search for users with a filter.

        Parameters:
            search_filter - LDAP filter string to match users against

        Returns: a dictionary mapping uids to attributes
        """

        if not self.connected(): raise LDAPException("Not connected!")

        search_filter = search_filter % tuple(self.escape(x) for x in params)

        # search for entries that match the filter
        try:
            matches = self.ldap.search_s(self.user_base, ldap.SCOPE_SUBTREE, search_filter)
        except ldap.LDAPError, e:
            raise LDAPException("user search failed: %s" % e)

        results = {}
        for match in matches:
            dn, attrs = match
            uid = attrs['uid'][0]
            results[uid] = attrs

        return results


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



    ### Account-related Methods ###

    def account_lookup(self, uid):
        """
        Retrieve the attributes of an account.

        Parameters:
            uid - the uid to look up

        Returns: attributes of user with uid
        """

        return self.user_lookup(uid, 'posixAccount')


    def account_search_id(self, uidNumber):
        """
        Retrieves a list of accounts with a certain UNIX uid number.

        LDAP (or passwd for that matter) does not enforce any restriction on
        the number of accounts that can have a certain UID number. Therefore
        this method returns a list of matches.

        Parameters:
            uidNumber - the user id of the accounts desired

        Returns: a dictionary mapping uids to attributes

        Example: connection.account_search_id(21292) -> {'mspang': { ... }}
        """

        search_filter = '(&(objectClass=posixAccount)(uidNumber=%s))'
        return self.user_search(search_filter, [ uidNumber ])


    def account_search_gid(self, gidNumber):
        """
        Retrieves a list of accounts with a certain UNIX gid
        number (search by default group).

        Returns: a dictionary mapping uids to attributes
        """

        search_filter = '(&(objectClass=posixAccount)(gidNumber=%s))'
        return self.user_search(search_filter, [ gidNumber ])


    def account_add(self, uid, cn, uidNumber, gidNumber, homeDirectory, loginShell=None, gecos=None, description=None, update=False):
        """
        Adds a user account to the directory.

        Parameters:
            uid           - the UNIX username for the account
            cn            - the real name of the member
            uidNumber     - the UNIX user id number
            gidNumber     - the UNIX group id number (default group)
            homeDirectory - home directory for the user
            loginShell    - login shell for the user
            gecos         - comment field (usually stores name etc)
            description   - description field (optional and unimportant)
            update        - if True, will update existing entries

        Example: connection.user_add('mspang', 'Michael Spang',
                     21292, 100, '/users/mspang', '/bin/bash',
                     'Michael Spang,,,')
        """

        if not self.connected(): raise LDAPException("Not connected!")

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
            attrs['loginShell'] = [ loginShell ]
        if description:
            attrs['description'] = [ description ]

        try:

            old_entry = self.user_lookup(uid)
            if old_entry and 'posixAccount' not in old_entry['objectClass'] and update:

                attrs.update(old_entry)
                attrs['objectClass'] = list(attrs['objectClass'])
                attrs['objectClass'].append('posixAccount')
                if not 'shadowAccount' in attrs['objectClass']:
                    attrs['objectClass'].append('shadowAccount')

                modlist = ldap.modlist.modifyModlist(old_entry, attrs)
                self.ldap.modify_s(dn, modlist)

            else:

                modlist = ldap.modlist.addModlist(attrs)
                self.ldap.add_s(dn, modlist)

        except ldap.LDAPError, e:
            raise LDAPException("unable to add: %s" % e)



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
        return self.lookup(dn, 'posixGroup')


    def group_search_id(self, gidNumber):
        """
        Retrieves a list of groups with the specified UNIX group number.
        
        Returns: a list of groups with gid gidNumber

        Example: connection.group_search_id(1001) -> ['office']
        """

        if not self.connected(): raise LDAPException("Not connected!")

        # search for posixAccount entries with the specified uidNumber
        try:
            search_filter = '(&(objectClass=posixGroup)(gidNumber=%d))' % gidNumber
            matches = self.ldap.search_s(self.group_base, ldap.SCOPE_SUBTREE, search_filter)
        except ldap.LDAPError, e:
            raise LDAPException("group search failed: %s" % e)

        # list for groups found
        group_cns = []

        results = {}
        for match in matches:
            dn, attrs = match
            uid = attrs['cn'][0]
            results[uid] = attrs

        return results


    def group_add(self, cn, gidNumber, description=None):
        """
        Adds a group to the directory.

        Example: connection.group_add('office', 1001, 'Office Staff')
        """

        if not self.connected(): raise LDAPException("Not connected!")

        dn = 'cn=' + cn + ',' + self.group_base
        attrs = {
            'objectClass': [ 'top', 'posixGroup', 'group' ],
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

        if not self.connected(): raise LDAPException("Not connected!")

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

        if not self.connected(): raise LDAPException("Not connected!")

        try:
            dn = 'cn=' + cn + ',' + self.group_base
            self.ldap.delete_s(dn)
        except ldap.LDAPError, e:
            raise LDAPException("unable to delete group: %s" % e)



    ### Member-related Methods ###

    def member_lookup(self, uid):
        """
        Retrieve the attributes of a member. This method will only return
        results that have the objectClass 'member'.

        Parameters:
            uid - the username to look up

        Returns: attributes of member with uid

        Example: connection.member_lookup('mspang') ->
                     { 'uid': 'mspang', 'uidNumber': 21292 ...}
        """

        if not self.connected(): raise LDAPException("Not connected!")

        dn = 'uid=' + uid + ',' + self.user_base
        return self.lookup(dn, 'member')


    def member_search_name(self, name):
        """
        Retrieves a list of members with the specified name (fuzzy).

        Returns: a dictionary mapping uids to attributes
        """

        search_filter = '(&(objectClass=member)(cn~=%s))'
        return self.user_search(search_filter, [ name ] )


    def member_search_term(self, term):
        """
        Retrieves a list of members who were registered in a certain term.

        Returns: a dictionary mapping uids to attributes
        """

        search_filter = '(&(objectClass=member)(term=%s))'
        return self.user_search(search_filter, [ term ])


    def member_search_program(self, program):
        """
        Retrieves a list of members in a certain program (fuzzy).

        Returns: a dictionary mapping uids to attributes
        """

        search_filter = '(&(objectClass=member)(program~=%s))'
        return self.user_search(search_filter, [ program ])


    def member_add(self, uid, cn, program=None, description=None):
        """
        Adds a member to the directory.

        Parameters:
            uid           - the UNIX username for the member
            cn            - the real name of the member
            program       - the member's program of study
            description   - a description for the entry
        """

        dn = 'uid=' + uid + ',' + self.user_base
        attrs = {
            'objectClass': [ 'top', 'account', 'member' ],
            'uid': [ uid ],
            'cn': [ cn ],
        }

        if program:
            attrs['program'] = [ program ]
        if description:
            attrs['description'] = [ description ]

        try:
            modlist = ldap.modlist.addModlist(attrs)
            self.ldap.add_s(dn, modlist)
        except ldap.LDAPError, e:
            raise LDAPException("unable to add: %s" % e)


    def member_add_account(self, uid, uidNumber, gidNumber, homeDirectory, loginShell=None, gecos=None):
        """
        Adds login privileges to a member.
        """

        return self.account_add(uid, None, uidNumber, gidNumber, homeDirectory, loginShell, gecos, None, True)



    ### Miscellaneous Methods ###

    def escape(self, value):
        """
        Escapes special characters in a value so that it may be safely inserted
        into an LDAP search filter.
        """

        value = str(value)
        value = value.replace('\\', '\\5c').replace('*', '\\2a')
        value = value.replace('(', '\\28').replace(')', '\\29')
        value = value.replace('\x00', '\\00')
        return value


    def used_uids(self, minimum=None, maximum=None):
        """
        Compiles a list of used UIDs in a range.

        Parameters:
            minimum - smallest uid to return in the list
            maximum - largest uid to return in the list

        Returns: list of integer uids

        Example: connection.used_uids(20000, 40000) -> [20000, 20001, ...]
        """

        if not self.connected(): raise LDAPException("Not connected!")

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

        if not self.connected(): raise LDAPException("Not connected!")

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


    def make_modlist(self, old, new):
        keys = set(old.keys()).union(set(new))
        mlist = []
        for key in keys:
            if key in old and not key in new:
                mlist.append((ldap.MOD_DELETE, key, list(set(old[key]))))
            elif key in new and not key in old:
                mlist.append((ldap.MOD_ADD, key, list(set(new[key]))))
            else:
                to_add = list(set(new[key]) - set(old[key]))
                if len(to_add) > 0:
                    mlist.append((ldap.MOD_ADD, key, to_add))
                to_del = list(set(old[key]) - set(new[key]))
                if len(to_del) > 0:
                    mlist.append((ldap.MOD_DELETE, key, to_del))
        return mlist


class Sasl:

    CB_USER = 0x4001
    bind_dn = 'dn:uid=%s,cn=%s,cn=%s,cn=auth'

    def __init__(self, mech, realm, userid, password):
        self.mech = mech
        self.bind_dn = self.bind_dn % (userid, realm, mech)

        if mech == 'GSSAPI':
            type, arg = password
            kinit = '/usr/bin/kinit'
            kinit_args = [ 'kinit', '%s@%s' % (userid, realm) ]
            if type == 'keytab':
                kinit_args += [ '-k', '-t', arg ]
            pid, kinit_out, kinit_in = ipc.popeni(kinit, kinit_args)
            os.waitpid(pid, 0)

    def callback(self, id, challenge, prompt, defresult):
        if id == self.CB_USER:
            return self.bind_dn
        else:
            return None


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
    tmname = 'testmember'
    tmrname = 'Test Member'
    tmprogram = 'UBW'
    tmdesc = 'Test Description'
    cushell = '/bin/true'
    cuhome = '/home/changed'
    curname = 'Test Modified User'
    cmhome = '/home/testmember'
    cmshell = '/bin/false'
    cmgecos = 'Test Member,,,'

    test(LDAPConnection)
    connection = LDAPConnection()
    success()

    test(LDAPConnection.disconnect)
    connection.disconnect()
    success()

    test(LDAPConnection.connect)
    connection.connect(srvurl, binddn, bindpw, ubase, gbase)
    if not connection.connected():
        fail("not connected")
    success()

    try:
        connection.user_delete(tuname)
        connection.user_delete(tmname)
        connection.group_delete(tgname)
    except LDAPException:
        pass

    test(LDAPConnection.used_uids)
    uids = connection.used_uids(minid, maxid)
    if type(uids) is not list:
        fail("list not returned")
    success()

    test(LDAPConnection.used_gids)
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

    test(LDAPConnection.account_add)
    connection.account_add(tuname, turname, tuuid, tugid, tuhome, tushell, tugecos)
    success()

    emdata = {
            'uid': [ tmname ],
            'cn': [ tmrname ],
            'program': [ tmprogram ],
            'description': [ tmdesc ],
    }

    test(LDAPConnection.member_add)
    connection.member_add(tmname, tmrname, tmprogram, tmdesc)
    success()

    tggid = unusedids.pop()
    egdata = {
            'cn': [ tgname ],
            'gidNumber': [ str(tggid) ]
            }

    test(LDAPConnection.group_add)
    connection.group_add(tgname, tggid)
    success()

    test(LDAPConnection.account_lookup)
    udata = connection.account_lookup(tuname)
    if udata: del udata['objectClass']
    assert_equal(eudata, udata)
    success()

    test(LDAPConnection.member_lookup)
    mdata = connection.member_lookup(tmname)
    if mdata: del mdata['objectClass']
    assert_equal(emdata, mdata)
    success()

    test(LDAPConnection.user_lookup)
    udata = connection.user_lookup(tuname)
    mdata = connection.user_lookup(tmname)
    if udata: del udata['objectClass']
    if mdata: del mdata['objectClass']
    assert_equal(eudata, udata)
    assert_equal(emdata, mdata)
    success()

    test(LDAPConnection.group_lookup)
    gdata = connection.group_lookup(tgname)
    if gdata: del gdata['objectClass']
    assert_equal(egdata, gdata)
    success()

    test(LDAPConnection.account_search_id)
    eulist = [ tuname ]
    ulist = connection.account_search_id(tuuid).keys()
    assert_equal(eulist, ulist)
    success()

    test(LDAPConnection.account_search_gid)
    ulist = connection.account_search_gid(tugid)
    if tuname not in ulist:
        fail("%s not in %s" % (tuname, ulist))
    success()

    test(LDAPConnection.member_search_name)
    mlist = connection.member_search_name(tmrname)
    if tmname not in mlist:
        fail("%s not in %s" % (tmname, mlist))
    success()

    test(LDAPConnection.member_search_program)
    mlist = connection.member_search_program(tmprogram)
    if tmname not in mlist:
        fail("%s not in %s" % (tmname, mlist))
    success()

    test(LDAPConnection.group_search_id)
    glist = connection.group_search_id(tggid).keys()
    eglist = [ tgname ]
    assert_equal(eglist, glist)
    success()

    ecudata = connection.account_lookup(tuname)
    ecudata['loginShell'] = [ cushell ]
    ecudata['homeDirectory'] = [ cuhome ]
    ecudata['cn'] = [ curname ]

    test(LDAPConnection.user_modify)
    connection.user_modify(tuname, ecudata)
    cudata = connection.account_lookup(tuname)
    assert_equal(ecudata, cudata)
    success()

    tmuid = unusedids.pop()
    tmgid = unusedids.pop()
    emadata = emdata.copy()
    emadata.update({
            'loginShell': [ cmshell ],
            'uidNumber': [ str(tmuid) ],
            'gidNumber': [ str(tmgid) ],
            'gecos': [ cmgecos ],
            'homeDirectory': [ cmhome ],
            })

    test(LDAPConnection.member_add_account)
    connection.member_add_account(tmname, tmuid, tmuid, cmhome, cmshell, cmgecos)
    success()

    ecgdata = connection.group_lookup(tgname)
    ecgdata['memberUid'] = [ tuname ]

    test(LDAPConnection.group_modify)
    connection.group_modify(tgname, ecgdata)
    cgdata = connection.group_lookup(tgname)
    assert_equal(ecgdata, cgdata)
    success()

    test(LDAPConnection.group_delete)
    connection.group_delete(tgname)
    success()

    test(LDAPConnection.disconnect)
    connection.disconnect()
    success()
