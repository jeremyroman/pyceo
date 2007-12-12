import urwid
from csc.apps.urwid.widgets import *
from csc.apps.urwid.window import *

from csc.adm import members
from csc.common.excep import InvalidArgument

position_data = [
    ('president',       'President'),
    ('vice-president',  'Vice-president'),
    ('treasurer',       'Treasurer'),
    ('secretary',       'Secretary'),
    ('sysadmin',        'System Administrator'),
    ('librarian',       'Librarian'),
    ('imapd',           'Imapd'),
    ('webmaster',       'Web Master'),
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
            widget = WordEdit("%s: " % text)
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
        for (position, info) in self.state['positions'].iteritems():
            members.set_position(position, info)
        self.headtext.set_text("Positions Updated")
        self.midtext.set_text("Congratulations, positions have been updated. "
            "You should rebuild the website in order to update the Positions "
            "page.")
    def check(self):
        pop_window()
