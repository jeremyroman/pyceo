import urwid
from ceo import members
from ceo.excep import InvalidArgument
from ceo.urwid.widgets import *
from ceo.urwid.window import *

class InfoPage(WizardPanel):
    def init_widgets(self):
        self.userid = urwid.Text("")
        self.name = urwid.Text("")
        self.terms = urwid.Text("")
        self.program = urwid.Text("")

        self.widgets = [
            urwid.Text( "Member Details" ),
            urwid.Divider(),
            self.name,
            self.userid,
            self.program,
            urwid.Divider(),
            self.terms,
        ]
    def focusable(self):
        return False
    def activate(self):
        member  = self.state.get('member', {})
        name    = member.get('cn', [''])[0]
        userid  = self.state['userid']
        program = member.get('program', [''])[0]
        terms   = member.get('term', [])

        self.name.set_text("Name: %s" % name)
        self.userid.set_text("User: %s" % userid)
        self.program.set_text("Program: %s" % program)
        self.terms.set_text("Terms: %s" % ", ".join(terms))
    def check(self):
        pop_window()
