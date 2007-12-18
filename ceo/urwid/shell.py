import urwid, ldap, pwd, os
from ceo import members, terms, ldapi
from ceo.urwid.widgets import *
from ceo.urwid.window import *

class IntroPage(WizardPanel):
    def init_widgets(self):
        self.widgets = [
            urwid.Text( "Changing Login Shell" ),
            urwid.Divider(),
            urwid.Text( "You can change your shell here. Request more shells "
                        "by emailing systems-committee." )
        ]
    def focusable(self):
        return False

class YouPage(WizardPanel):
    def init_widgets(self):
        you = pwd.getpwuid(os.getuid()).pw_name
        self.userid = LdapWordEdit(csclub_uri, csclub_base, 'uid',
            "Username: ", you)

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

class ShellPage(WizardPanel):
    def init_widgets(self):
        self.midtext = urwid.Text("")

        self.widgets = [
            urwid.Text("Choose a Shell"),
            urwid.Divider(),
        ]

        def set_shell(radio_button, new_state, shell):
            if new_state:
                self.state['shell'] = shell

        radio_group = []
        self.shells = members.get_shells()
        self.shellw = [ urwid.RadioButton(radio_group, shell,
            on_state_change=set_shell, user_data=shell)
            for shell in self.shells ]

        self.widgets.extend(self.shellw)
    def set_shell(self, shell):
        i = self.shells.index(shell)
        self.shellw[i].set_state(True)
    def focusable(self):
        return True
    def activate(self):
        self.set_shell(self.state['member']['loginShell'][0])

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
            user, shell = self.state['userid'], self.state['shell']
            members.set_shell(user, shell)
            self.headtext.set_text("Login Shell Changed")
            self.midtext.set_text("The shell for %s has been changed to %s."
                                  % (user, shell))
        except ldap.LDAPError, e:
            problem = ldapi.format_ldaperror(e)
        except members.MemberException, e:
            problem = str(e)
        if problem:
            self.headtext.set_text("Failed to Change Shell")
            self.midtext.set_text("Perhaps you don't have permission to change %s's shell? "
                    "The error was:\n\n%s" % (user, problem))
    def check(self):
        pop_window()
