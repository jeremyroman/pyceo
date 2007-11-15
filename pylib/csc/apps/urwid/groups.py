import urwid
from csc.apps.urwid.widgets import *
from csc.apps.urwid.window import *

from csc.adm import accounts, members
from csc.common.excep import InvalidArgument

class ChangeMember(WizardPanel):
    def __init__(self, state, data):
        state['data'] = data
        WizardPanel.__init__(self, state)
    def init_widgets(self):
        self.userid = WordEdit("Username: ")

        data = self.state['data']
        self.widgets = [
            urwid.Text( "%s %s Member" % (data['type'], data['name']) ),
            urwid.Divider(),
            self.userid,
        ]
    def check(self):
        self.state['userid'] = self.userid.get_edit_text()
        if self.state['userid']:
            if not members.connected(): members.connect()
            self.state['member'] = members.get(self.userid.get_edit_text())
        if not self.state['member']:
            set_status("Member not found")
            self.focus_widget(self.userid)
            return True
        clear_status()

class EndPage(WizardPanel):
    def init_widgets(self):
        self.headtext = urwid.Text("")
        self.midtext = urwid.Text("")
        self.widgets = [
            self.headtext,
            urwid.Divider(),
            self.midtext,
        ]
    def focusable(self):
        return False
    def check(self):
        pop_window()
    def activate(self):
        data = self.state['data']
        type = data['type'].lower()
        failed = []
        for group in data['groups']:
            try:
                members.change_group_member(type, group, self.state['userid'])
            except:
                failed.append(group)
        if len(failed) == 0:
            self.headtext.set_text("%s succeeded" % data['type'])
            self.midtext.set_text("Congratulations, the group modification "
                "has succeeded.")
        else:
            self.headtext.set_text("%s partially succeeded" % data['type'])
            self.midtext.set_text("Failed to %s member to %s for the "
                "following groups: %s. This may indicate an attempt to add a "
                "duplicate group member or to delete a non-present group "
                "member." % (data['type'].lower(), data['name'],
                ', '.join(failed)))
