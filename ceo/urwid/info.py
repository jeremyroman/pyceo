import urwid
from ceo.urwid.widgets import *
from ceo.urwid.window import *

class InfoPage(WizardPanel):
    def init_widgets(self):
        self.userid = urwid.Text("")
        self.name = urwid.Text("")
        self.terms = urwid.Text("")
        self.nmterms = urwid.Text("")
        self.program = urwid.Text("")

        self.widgets = [
            urwid.Text( "Member Details" ),
            urwid.Divider(),
            self.name,
            self.userid,
            self.program,
            urwid.Divider(),
            self.terms,
            self.nmterms,
        ]
    def focusable(self):
        return False
    def activate(self):
        member  = self.state.get('member', {})
        name    = member.get('cn', [''])[0]
        userid  = self.state['userid']
        program = member.get('program', [''])[0]
        shell   = member.get('loginShell', [''])[0]
        terms   = member.get('term', [])
        nmterms = member.get('nonMemberTerm', [])

        self.name.set_text("Name: %s" % name)
        self.userid.set_text("User: %s" % userid)
        self.program.set_text("Program: %s" % program)
        self.program.set_text("Shell: %s" % shell)
        if terms:
            self.terms.set_text("Terms: %s" % ", ".join(terms))
        if nmterms:
            self.nmterms.set_text("Rep Terms: %s" % ", ".join(nmterms))
    def check(self):
        pop_window()
