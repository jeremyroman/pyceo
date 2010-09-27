import urwid, ldap, sys
from ceo.urwid.window import raise_back, push_window
import ceo.ldapi as ldapi

#Todo: kill ButtonText because no one uses it except one place and we can probably do that better anyway

csclub_uri = "ldap://ldap1.csclub.uwaterloo.ca/ ldap://ldap2.csclub.uwaterloo.ca"
csclub_base = "dc=csclub,dc=uwaterloo,dc=ca"

def make_menu(items):
    items = [ urwid.AttrWrap( ButtonText( cb, data, txt ), 'menu', 'selected') for (txt, cb, data) in items ]
    return ShortcutListBox(items)

def labelled_menu(itemses):
    widgets = []
    for label, items in itemses:
        if label:
            widgets.append(urwid.Text(label))
        widgets += (urwid.AttrWrap(ButtonText(cb, data, txt), 'menu', 'selected') for (txt, cb, data) in items)
        widgets.append(urwid.Divider())
    widgets.pop()
    return ShortcutListBox(widgets)

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

#DONTUSE
class CaptionedText(urwid.Text):
    def __init__(self, caption, *args, **kwargs):
        self.caption = caption
        urwid.Text.__init__(self, *args, **kwargs)
    def render(self, *args, **kwargs):
        self.set_text(self.caption + self.get_text()[0])
        urwid.Text.render(*args, **kwargs)

class SingleEdit(urwid.Edit):
    def keypress(self, size, key):
        key_mappings = {
            'enter': 'down',
            'tab': 'down',
            'shift tab': 'up',
            'ctrl a': 'home',
            'ctrl e': 'end'
        }
        
        if key in key_mappings:
            return urwid.Edit.keypress(self, size, key_mappings[key])
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
    index = None

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
        if (key == 'tab' or key == 'shift tab') and self.ldap != None:
            if self.index != None:
                if key == 'tab':
                    self.index = (self.index + 1) % len(self.choices)
                elif key == 'shift tab':
                    self.index = (self.index - 1) % len(self.choices)
                text = self.choices[self.index]
                self.set_edit_text(text)
                self.set_edit_pos(len(text))
            else:
                try:
                    text = self.get_edit_text()
                    search = ldapi.escape(text)
                    matches = self.ldap.search_s(self.base,
                        ldap.SCOPE_SUBTREE, '(%s=%s*)' % (self.attr, search))
                    self.choices = [ text ]
                    for match in matches:
                        (_, attrs) = match
                        self.choices += attrs['uid']
                    self.choices.sort()
                    self.index = 0
                    self.keypress(size, key)
                except ldap.LDAPError, e:
                    pass
        else:
            self.index = None
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

class EnhancedButton(urwid.Button):
    def keypress(self, size, key):
        if key == 'tab':
            return urwid.Button.keypress(self, size, 'down')
        elif key == 'shift tab':
            return urwid.Button.keypress(self, size, 'up')
        else:
            return urwid.Button.keypress(self, size, key)

class Wizard(urwid.WidgetWrap):
    def __init__(self):
        self.selected = None
        self.panels = []

        self.panelwrap = urwid.WidgetWrap( urwid.SolidFill() )
        self.back = EnhancedButton("Back", self.back)
        self.next = EnhancedButton("Next", self.next)
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
            self.panelwrap._w = self.panels[panelno]
            self.panelwrap._invalidate()
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

# assumes that a SimpleListWalker containing
# urwid.Text or subclass is used
class ShortcutListBox(urwid.ListBox):
    def keypress(self, size, key):
        # only process single letters; pass all else to super
        if len(key) == 1 and key.isalpha():
            next = self.get_focus()[1] + 1
            shifted_contents = self.body.contents[next:] + self.body.contents[:next]

            # find the next item matching the letter requested
            try:
                new_focus = (i for i,w in enumerate(shifted_contents)
                             if w.selectable() and w.text[0].upper() == key.upper()).next()
                new_focus = (new_focus + next) % len(self.body.contents)
                self.set_focus(new_focus)
            except:
                # ring the bell if it isn't found
                sys.stdout.write('\a')
        else:
            urwid.ListBox.keypress(self, size, key)
