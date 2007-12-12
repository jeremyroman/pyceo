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
from subprocess import Popen, PIPE


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


    def connect_sasl(self, uri, mech, realm, userid, password, user_base, group_base):

        # open the connection
        self.ldap = ldap.initialize(uri)

        # authenticate
        sasl = Sasl(mech, realm, userid, password)
        self.ldap.sasl_interactive_bind_s('', sasl)

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

    def __init__(self, mech, realm, userid, password):
        self.mech = mech
        if mech == 'GSSAPI':
            credtype, cred = password
            kinit_args = [ '/usr/bin/kinit', '%s@%s' % (userid, realm) ]
            if credtype == 'keytab':
                kinit_args += [ '-kt', cred ]

            kinit = Popen(kinit_args, stdin=PIPE, stdout=PIPE, stderr=PIPE)
            kinit.wait()

    def callback(self, id, challenge, prompt, defresult):
        return ''
