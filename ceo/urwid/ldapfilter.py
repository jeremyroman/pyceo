import ldap

class LdapFilter:
    def __init__(self, widget):
        self.widget = widget

    def set_ldap_filter(self, ldap_uri, ldap_base, ldap_attr, ldap_map):
        try:
            self.ldap = ldap.initialize(ldap_uri)
            self.ldap.simple_bind_s("", "")
        except ldap.LDAPError:
            return
        self.base = ldap_base
        self.attr = ldap_attr
        self.map = ldap_map

    def keypress(self, size, key):
        if self.ldap != None:
            if key == 'enter' or key == 'down' or key == 'up':
                attr = self.escape(self.attr)
                search = self.escape(self.widget.get_edit_text(self))
                ldfilter = '(%s=%s)' % (attr, search)
                try:
                    matches = self.ldap.search_s(self.base,
                        ldap.SCOPE_SUBTREE, ldfilter)
                    if len(matches) > 0:
                        (_, attrs) = matches[0]
                        for (k, v) in self.map.items():
                            if attrs.has_key(k) and len(attrs[k]) > 0:
                                v.set_edit_text(attrs[k][0])
                except ldap.LDAPError:
                    pass
        return self.widget.keypress(self, size, key)

    def escape(self, value):
        value = str(value)
        value = value.replace('\\', '\\5c').replace('*', '\\2a')
        value = value.replace('(', '\\28').replace(')', '\\29')
        value = value.replace('\x00', '\\00')
        return value
