import urwid, ldap
from ceo import members, terms, ldapi
from ceo.urwid.widgets import *
from ceo.urwid.window import *

class IntroPage(WizardPanel):
    def init_widgets(self):
        self.widgets = [
            urwid.Text( "Renewing Membership" ),
            urwid.Divider(),
            urwid.Text( "CSC membership is $2.00 per term. You may pre-register "
                        "for future terms if desired." )
        ]
    def focusable(self):
        return False

class UserPage(WizardPanel):
    def init_widgets(self):
        self.userid = WordEdit("Username: ")

        self.widgets = [
            urwid.Text( "Member Information" ),
            urwid.Divider(),
            self.userid,
        ]
    def check(self):
        self.state['userid'] = self.userid.get_edit_text()
        self.state['member'] = None
        if self.state['userid']:
            self.state['member'] = members.get(self.userid.get_edit_text())
        if not self.state['member']:
            set_status("Member not found")
            self.focus_widget(self.userid)
            return True

class TermPage(WizardPanel):
    def init_widgets(self):
        self.start = SingleEdit("Start: ")
        self.count = SingleIntEdit("Count: ")

        self.widgets = [
            urwid.Text( "Terms to Register" ),
            urwid.Divider(),
            self.start,
            self.count,
        ]
    def activate(self):
        if not self.start.get_edit_text():
            old_terms = []
            if 'term' in self.state['member']:
                old_terms = self.state['member']['term']
            self.start.set_edit_text( terms.next_unregistered( old_terms ) )
            self.count.set_edit_text( "1" )
    def check(self):
        try:
            self.state['terms'] = terms.interval( self.start.get_edit_text(), self.count.value() )
        except Exception, e:
            self.focus_widget( self.start )
            set_status( "Invalid start term" )
            return True
        for term in self.state['terms']:
            if members.registered( self.state['userid'], term):
                self.focus_widget( self.start )
                set_status( "Already registered for " + term )
                return True
        if len(self.state['terms']) == 0:
            self.focus_widget(self.count)
            set_status( "Registering for zero terms?" )
            return True

class PayPage(WizardPanel):
    def init_widgets(self):
        self.midtext = urwid.Text("")

        self.widgets = [
            urwid.Text("Membership Fee"),
            urwid.Divider(),
            self.midtext,
        ]
    def focusable(self):
        return False
    def activate(self):
        regterms = self.state['terms']
        plural = "term"
        if len(self.state['terms']) > 1:
            plural = "terms"
        self.midtext.set_text("You are registering for %d %s, and owe the "
                       "Computer Science Club $%d.00 in membership fees. "
                       "Please deposit the money in the safe before "
                       "continuing. " % ( len(regterms), plural, len(regterms * 2)))

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
    def activate(self):
        problem = None
        try:
            members.register( self.state['userid'], self.state['terms'] )
            self.headtext.set_text("Registration Succeeded")
            self.midtext.set_text("The member has been registered for the following "
                             "terms: " + ", ".join(self.state['terms']) + ".")
        except ldap.LDAPError, e:
            problem = ldapi.format_ldaperror(e)
        except members.MemberException, e:
            problem = str(e)
        if problem:
            self.headtext.set_text("Failed to Register")
            self.midtext.set_text("You may refund any fees paid or retry. "
                             "The error was:\n\n%s" % problem)

    def check(self):
        pop_window()
