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

class ClubUserIntroPage(IntroPage):
    def init_widgets(self):
        self.widgets = [
            urwid.Text( "Renewing Club User Account" ),
            urwid.Divider(),
            urwid.Text( "In order for clubs to maintain websites hosted by "
                        "the Computer Science Club, they need access to our "
                        "machines. We grant accounts to club users at no charge "
                        "in order to provide this access. Registering a user "
                        "in this way grants one term of free access to our "
                        "machines, without any other membership privileges "
                        "(they can't vote, hold office, etc). If such a user "
                        "decides to join, use the Renew Membership option." )
        ]

class UserPage(WizardPanel):
    def init_widgets(self):
        self.userid = LdapWordEdit(csclub_uri, csclub_base, 'uid',
            "Username: ")

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

class EmailPage(WizardPanel):
    def init_widgets(self):
        self.email = SingleEdit("Email: ")

        self.widgets = [
            urwid.Text( "Mail Forwarding" ),
            urwid.Divider(),
            urwid.Text("Please ensure the forwarding address for your CSC "
                "email is up to date. You may leave this blank if you do not "
                "want your CSC email forwarded, and intend to log in "
                "regularly to check it."),
            urwid.Divider(),
            urwid.Text("Warning: Changing this overwrites ~/.forward"),
            urwid.Divider(),
            self.email,
        ]
    def activate(self):
        cfwd = members.current_email(self.state['userid'])
        self.state['old_forward'] = cfwd if cfwd else ''
        self.email.set_edit_text(self.state['old_forward'])
    def check(self):
        fwd = self.email.get_edit_text().strip().lower()
        if fwd:
            msg = members.check_email(fwd)
            if msg:
                set_status(msg)
                return True
            if fwd == '%s@csclub.uwaterloo.ca' % self.state['userid']:
                set_status('You cannot forward your address to itself. Leave it blank to disable forwarding.')
                return True
        self.state['new_forward'] = fwd

class EmailDonePage(WizardPanel):
    def init_widgets(self):
        self.status = urwid.Text("")
        self.widgets = [
            urwid.Text("Mail Forwarding"),
            urwid.Divider(),
            self.status,
        ]
    def focusable(self):
        return False
    def activate(self):
        if self.state['old_forward'] == self.state['new_forward']:
            if self.state['old_forward']:
                self.status.set_text(
                    'You have chosen to leave your forwarding address '
                    'as %s. Make sure to check this email for updates '
                    'from the CSC.' % self.state['old_forward'])
            else:
                self.status.set_text(
                    'You have chosen not to set a forwarding address. '
                    'Please check your CSC email regularly (via IMAP, POP, or locally) '
                    'for updates from the CSC.'
                    '\n\n'
                    'Note: If you do have a ~/.forward, we were not able to read it or '
                    'it was not a single email address. Do not worry, we have left it '
                    'as is.')
        else:
            try:
                msg = members.change_email(self.state['userid'], self.state['new_forward'])
                if msg:
                    self.status.set_text("Errors occured updating your forwarding address:"
                                         "\n\n%s" % msg)
                else:
                    if self.state['new_forward']:
                        self.status.set_text(
                            'Your email forwarding address has been successfully set '
                            'to %s. Test it out by emailing %s@csclub.uwaterloo.ca and '
                            'making sure you receive it at your forwarding address.'
                            % (self.state['new_forward'], self.state['userid']))
                    else:
                        self.status.set_text(
                            'Your email forwarding address has been successfully cleared. '
                            'Please check your CSC email regularly (via IMAP, POP, or locally) '
                            'for updates from the CSC.')
            except Exception, e:
                self.status.set_text(
                    'An exception occured updating your email:\n\n%s' % e)

class TermPage(WizardPanel):
    def __init__(self, state, utype='member'):
        self.utype = utype
        WizardPanel.__init__(self, state)
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
            self.terms = self.state['member'].get('term', [])
            self.nmterms = self.state['member'].get('nonMemberTerm', [])

            if self.utype == 'member':
                self.start.set_edit_text( terms.next_unregistered( self.terms ) )
            else:
                self.start.set_edit_text( terms.next_unregistered( self.terms + self.nmterms ) )

            self.count.set_edit_text( "1" )
    def check(self):
        try:
            self.state['terms'] = terms.interval( self.start.get_edit_text(), self.count.value() )
        except Exception, e:
            self.focus_widget( self.start )
            set_status( "Invalid start term" )
            return True
        for term in self.state['terms']:
            if self.utype == 'member':
                already = term in self.terms
            else:
                already = term in self.terms or term in self.nmterms

            if already:
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
    def __init__(self, state, utype='member'):
        self.utype = utype
        WizardPanel.__init__(self, state)
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
            self.headtext.set_text("Registration Succeeded")
            if self.utype == 'member':
                members.register( self.state['userid'], self.state['terms'] )
                self.midtext.set_text("The member has been registered for the following "
                                 "terms: " + ", ".join(self.state['terms']) + ".")
            else:
                members.register_nonmember( self.state['userid'], self.state['terms'] )
                self.midtext.set_text("The club user has been registered for the following "
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
