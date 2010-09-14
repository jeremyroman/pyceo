import urwid
from ceo import members
from ceo.urwid.widgets import *
from ceo.urwid.window import *

position_data = [
    ('president',       'President'),
    ('vice-president',  'Vice-president'),
    ('treasurer',       'Treasurer'),
    ('secretary',       'Secretary'),
    ('sysadmin',        'System Administrator'),
    ('cro',             'Chief Returning Officer'),
    ('librarian',       'Librarian'),
    ('imapd',           'Imapd'),
    ('webmaster',       'Web Master'),
    ('offsck',          'Office Manager'),
]

class IntroPage(WizardPanel):
    def init_widgets(self):
        self.widgets = [
            urwid.Text( "Managing Positions" ),
            urwid.Divider(),
            urwid.Text( "Enter a username for each position. If a position is "
                        "held by multiple people, enter a comma-separated "
                        "list of usernames. If a position is held by nobody "
                        "leave the username blank." ),
        ]
    def focusable(self):
        return False

class InfoPage(WizardPanel):
    def init_widgets(self):
        self.widgets = [
            urwid.Text( "Positions" ),
            urwid.Divider(),
        ]
        positions = members.list_positions()
        self.position_widgets = {}
        for (position, text) in position_data:
            widget = LdapWordEdit(csclub_uri, csclub_base, 'uid',
                "%s: " % text)
            if position in positions:
                widget.set_edit_text(','.join(positions[position].keys()))
            else:
                widget.set_edit_text('')
            self.position_widgets[position] = widget
            self.widgets.append(widget)

    def parse(self, entry):
        if len(entry) == 0:
            return []
        return entry.split(',')

    def check(self):
        self.state['positions'] = {}
        for (position, widget) in self.position_widgets.iteritems():
            self.state['positions'][position] = \
                self.parse(widget.get_edit_text())
            for p in self.state['positions'][position]:
                if members.get(p) == None:
                    self.focus_widget(widget)
                    set_status( "Invalid username: '%s'" % p )
                    return True
        clear_status()

class EndPage(WizardPanel):
    def init_widgets(self):
        old = members.list_positions()
        self.headtext = urwid.Text("")
        self.midtext = urwid.Text("")

        self.widgets = [
            self.headtext,
            urwid.Divider(),
            self.midtext,
        ]
    def focusable(self):
        return False
    def activate(self):
        failed = []
        for (position, info) in self.state['positions'].iteritems():
            try:
                members.set_position(position, info)
            except ldap.LDAPError:
                failed.append(position)
        if len(failed) == 0:
            self.headtext.set_text("Positions Updated")
            self.midtext.set_text("Congratulations, positions have been "
                "updated. You should rebuild the website in order to update "
                "the Positions page.")
        else:
            self.headtext.set_text("Positions Results")
            self.midtext.set_text("Failed to update the following positions: "
                "%s." % join(failed))
    def check(self):
        pop_window()
