"""
LDAP Utilities

This module makes use of python-ldap, a Python module with bindings
to libldap, OpenLDAP's native C client library.
"""
import ldap.modlist


def connect_sasl(uri, mech, realm):

    # open the connection
    ld = ldap.initialize(uri)

    # authenticate
    sasl = Sasl(mech, realm)
    ld.sasl_interactive_bind_s('', sasl)

    return ld


def abslookup(ld, dn, objectclass=None):

    # search for the specified dn
    try:
        if objectclass:
            search_filter = '(objectclass=%s)' % escape(objectclass)
            matches = ld.search_s(dn, ldap.SCOPE_BASE, search_filter)
        else:
            matches = ld.search_s(dn, ldap.SCOPE_BASE)
    except ldap.NO_SUCH_OBJECT:
        return None
            
    # dn was found, but didn't match the objectclass filter
    if len(matches) < 1:
        return None

    # return the attributes of the single successful match
    match = matches[0]
    match_dn, match_attributes = match
    return match_attributes


def lookup(ld, rdntype, rdnval, base, objectclass=None):
    dn = '%s=%s,%s' % (rdntype, escape(rdnval), base)
    return abslookup(ld, dn, objectclass)


def search(ld, base, search_filter, params, scope=ldap.SCOPE_SUBTREE, attrlist=None, attrsonly=0):

    real_filter = search_filter % tuple(escape(x) for x in params)

    # search for entries that match the filter
    matches = ld.search_s(base, scope, real_filter, attrlist, attrsonly)
    return matches


def modify(ld, rdntype, rdnval, base, mlist):
    dn = '%s=%s,%s' % (rdntype, escape(rdnval), base)
    ld.modify_s(dn, mlist)


def modify_attrs(ld, rdntype, rdnval, base, old, attrs):
    dn = '%s=%s,%s' % (rdntype, escape(rdnval), base)

    # build list of modifications to make
    changes = ldap.modlist.modifyModlist(old, attrs)

    # apply changes
    ld.modify_s(dn, changes)


def modify_diff(ld, rdntype, rdnval, base, old, new):
    dn = '%s=%s,%s' % (rdntype, escape(rdnval), base)

    # build list of modifications to make
    changes = make_modlist(old, new)

    # apply changes
    ld.modify_s(dn, changes)


def escape(value):
    """
    Escapes special characters in a value so that it may be safely inserted
    into an LDAP search filter.
    """

    value = str(value)
    value = value.replace('\\', '\\5c').replace('*', '\\2a')
    value = value.replace('(', '\\28').replace(')', '\\29')
    value = value.replace('\x00', '\\00')
    return value


def make_modlist(old, new):
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

    def __init__(self, mech, realm):
        self.mech = mech
        self.realm = realm

    def callback(self, id, challenge, prompt, defresult):
        return ''
