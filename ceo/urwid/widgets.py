import urwid, ldap
from ceo.urwid.window import raise_back, push_window
import ceo.ldapi as ldapi

uwldap_uri = "ldap://uwldap.uwaterloo.ca/"
uwldap_base = "dc=uwaterloo,dc=ca"
csclub_uri = "ldap://ldap1.csclub.uwaterloo.ca/ ldap://ldap2.csclub.uwaterloo.ca"
csclub_base = "dc=csclub,dc=uwaterloo,dc=ca"

def menu_items(items):
    return [ urwid.AttrWrap( ButtonText( cb, data, txt ), 'menu', 'selected') for (txt, cb, data) in items ]

def push_wizard(name, pages, dimensions=(50, 10)):
    state = {}
    wiz = Wizard()
    for page in pages:
        if type(page) != tuple:
            page = (page, )
        wiz.add_panel( page[0](state, *page[1:]) )
    push_window( urwid.Filler( urwid.Padding(
        urwid.LineBox(wiz), 'center', dimensions[0]),
        'middle', dimensions[1] ), name )

class ButtonText(urwid.Text):
    def __init__(self, callback, data, *args, **kwargs):
        self.callback = callback
        self.data = data
        urwid.Text.__init__(self, *args, **kwargs)
    def selectable(self):
        return True
    def keypress(self, size, key):
        if key == 'enter' and self.callback:
            self.callback(self.data)
        else:
            return key

class SingleEdit(urwid.Edit):
    def keypress(self, size, key):
        if key == 'enter':
            return urwid.Edit.keypress(self, size, 'down')
        else:
            return urwid.Edit.keypress(self, size, key)

class SingleIntEdit(urwid.IntEdit):
    def keypress(self, size, key):
        if key == 'enter':
            return urwid.Edit.keypress(self, size, 'down')
        else:
            return urwid.Edit.keypress(self, size, key)

class WordEdit(SingleEdit):
    def valid_char(self, ch):
        return urwid.Edit.valid_char(self, ch) and ch != ' '

class LdapWordEdit(WordEdit):
    ldap = None
    tabbing = False
    def __init__(self, uri, base, attr, *args):
        try:
            self.ldap = ldap.initialize(uri)
            self.ldap.simple_bind_s("", "")
        except ldap.LDAPError:
            return WordEdit.__init__(self, *args)
        self.base = base
        self.attr = ldapi.escape(attr)
        return WordEdit.__init__(self, *args)
    def keypress(self, size, key):
        if key == 'tab' and self.ldap != None:
            if self.tabbing:
                self.index = (self.index + 1) % len(self.choices)
                text = self.choices[self.index]
                self.set_edit_text(text)
                self.set_edit_pos(len(text))
            else:
                try:
                    search = ldapi.escape(self.get_edit_text())
                    matches = self.ldap.search_s(self.base,
                        ldap.SCOPE_SUBTREE, '(%s=%s*)' % (self.attr, search))
                    self.choices = []
                    for match in matches:
                        (_, attrs) = match
                        self.choices += attrs['uid']
                    if len(self.choices) > 0:
                        self.index = 0
                        self.tabbing = True
                        text = self.choices[self.index]
                        self.set_edit_text(text)
                        self.set_edit_pos(len(text))
                except ldap.LDAPError, e:
                    pass
        else:
            self.tabbing = False
            return WordEdit.keypress(self, size, key)

class LdapFilterWordEdit(LdapWordEdit):
    def __init__(self, uri, base, attr, map, *args):
        LdapWordEdit.__init__(self, uri, base, attr, *args)
        self.map = map
    def keypress(self, size, key):
        if self.ldap != None:
            if key == 'enter' or key == 'down' or key == 'up':
                search = ldapi.escape(self.get_edit_text())
                try:
                    matches = self.ldap.search_s(self.base,
                        ldap.SCOPE_SUBTREE, '(%s=%s)' % (self.attr, search))
                    if len(matches) > 0:
                        (_, attrs) = matches[0]
                        for (k, v) in self.map.items():
                            if attrs.has_key(k) and len(attrs[k]) > 0:
                                v.set_edit_text(attrs[k][0])
                except ldap.LDAPError:
                    pass
        return LdapWordEdit.keypress(self, size, key)

class PassEdit(SingleEdit):
    def get_text(self):
        text = urwid.Edit.get_text(self)
        return (self.caption + " " * len(self.get_edit_text()), text[1])

class Wizard(urwid.WidgetWrap):
    def __init__(self):
        self.selected = None
        self.panels = []

        self.panelwrap = urwid.WidgetWrap( urwid.SolidFill() )
        self.back = urwid.Button("Back", self.back)
        self.next = urwid.Button("Next", self.next)
        self.buttons = urwid.Columns( [ self.back, self.next ], dividechars=3, focus_column=1 )
        pad = urwid.Padding( self.buttons, ('fixed right', 2), 19 )
        self.pile = urwid.Pile( [self.panelwrap, ('flow', pad)], 0 )
        urwid.WidgetWrap.__init__(self, self.pile)

    def add_panel(self, panel):
        self.panels.append( panel )
        if len(self.panels) == 1:
            self.select(0)

    def select(self, panelno, set_focus=True):
        if 0 <= panelno < len(self.panels):
            self.selected = panelno
            self.panelwrap.set_w( self.panels[panelno] )
            self.panels[panelno].activate()

            if set_focus:
                if self.panels[panelno].focusable():
                    self.pile.set_focus( 0 )
                else:
                    self.pile.set_focus( 1 )

    def next(self, *args, **kwargs):
        if self.panels[self.selected].check():
            self.select( self.selected )
            return
        self.select(self.selected + 1)

    def back(self, *args, **kwargs):
        if self.selected == 0:
            raise_back()
        self.select(self.selected - 1, False)

class WizardPanel(urwid.WidgetWrap):
    def __init__(self, state):
        self.state = state
        self.init_widgets()
        self.box = urwid.ListBox( urwid.SimpleListWalker( self.widgets ) )
        urwid.WidgetWrap.__init__( self, self.box )
    def init_widgets(self):
        self.widgets = []
    def focus_widget(self, widget):
        self.box.set_focus( self.widgets.index( widget ) )
    def focusable(self):
        return True
    def check(self):
        return
    def activate(self):
        return
