import urwid
from ceo import members, terms
from ceo.excep import InvalidArgument
from ceo.urwid.widgets import *
from ceo.urwid.window import *

class IntroPage(WizardPanel):
    def init_widgets(self):
        self.widgets = [
            urwid.Text( "Joining the Computer Science Club" ),
            urwid.Divider(),
            urwid.Text( "CSC membership is $2.00 for one term. Please ensure "
                        "the fee is deposited into the safe before continuing." ),
        ]
    def focusable(self):
        return False

class ClubIntroPage(WizardPanel):
    def init_widgets(self):
        self.widgets = [
            urwid.Text( "Club Services" ),
            urwid.Divider(),
            urwid.Text( "We provide other UW clubs accounts for email and "
                        "web hosting, free of charge. Like members, clubs "
                        "get web hosting at %s. We can also arrange for "
                        "uwaterloo.ca subdomains; please instruct the club "
                        "representative to contact the systems committee "
                        "for more information."
                        "\n\nNote: This is not complete. Authorizing members "
                        "to access the club account still requires manual "
                        "intervention."
                        % "http://csclub.uwaterloo.ca/~clubid/"
            )
        ]
    def focusable(self):
        return False

class InfoPage(WizardPanel):
    def init_widgets(self):
        self.userid = LdapFilterWordEdit("UWuserid: ")
        self.name = SingleEdit("Full name: ")
        self.program = SingleEdit("Program of Study: ")
        self.userid.set_ldap_filter(
            "ldap://uwldap.uwaterloo.ca/", "dc=uwaterloo,dc=ca",
            "uid", {'cn':self.name, 'ou':self.program}
        )
        self.widgets = [
            urwid.Text( "Member Information - Please Check ID" ),
            urwid.Divider(),
            self.userid,
            self.name,
            self.program,
        ]
    def check(self):
        self.state['userid'] = self.userid.get_edit_text()
        self.state['name'] = self.name.get_edit_text()
        self.state['program'] = self.program.get_edit_text()

        if len( self.state['userid'] ) < 3:
            self.focus_widget( self.userid )
            set_status("Username is too short")
            return True
        elif len( self.state['name'] ) < 4:
            self.focus_widget( self.name )
            set_status("Name is too short")
            return True
        clear_status()

class ClubInfoPage(WizardPanel):
    def init_widgets(self):
        self.userid = WordEdit("Username: ")
        self.name = SingleEdit("Club Name: ")
        self.widgets = [
            urwid.Text( "Club Information" ),
            urwid.Divider(),
            self.userid,
            self.name,
        ]
    def check(self):
        self.state['userid'] = self.userid.get_edit_text()
        self.state['name'] = self.name.get_edit_text()

        if len( self.state['userid'] ) < 3:
            self.focus_widget( self.userid )
            set_status("Username is too short")
            return True
        elif len( self.state['name'] ) < 4:
            self.focus_widget( self.name )
            set_status("Name is too short")
            return True
        clear_status()

class SignPage(WizardPanel):
    def init_widgets(self):
        self.widgets = [
            urwid.Text( "Machine Usage Policy" ),
            urwid.Divider(),
            urwid.Text( "Ensure the new member has signed the "
                        "Machine Usage Policy. Accounts of users who have not "
                        "signed will be suspended if discovered." ),
        ]
    def focusable(self):
        return False

class PassPage(WizardPanel):
    def init_widgets(self):
        self.password = PassEdit("Password: ")
        self.pwcheck = PassEdit("Re-enter: ")
        self.widgets = [
            urwid.Text( "Member Password" ),
            urwid.Divider(),
            self.password,
            self.pwcheck,
        ]
    def focus_widget(self, widget):
        self.box.set_focus( self.widgets.index( widget ) )
    def clear_password(self):
        self.focus_widget( self.password )
        self.password.set_edit_text("")
        self.pwcheck.set_edit_text("")
    def check(self):
        self.state['password'] = self.password.get_edit_text()
        pwcheck = self.pwcheck.get_edit_text()

        if self.state['password'] != pwcheck:
            self.clear_password()
            set_status("Passwords do not match")
            return True
        elif len(self.state['password']) < 5:
            self.clear_password()
            set_status("Password is too short")
            return True
        clear_status()

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
    def check(self):
        pop_window()
    def activate(self):
        problem = None
        try:
            if self.utype == 'member':
                members.create_member( self.state['userid'], self.state['password'], self.state['name'], self.state['program'] )
                members.register( self.state['userid'], terms.current() )
            elif self.utype == 'club':
                members.create_club( self.state['userid'], self.state['name'] )
            else:
                raise Exception("Internal Error")
        except members.InvalidArgument, e:
            problem = str(e)
        except members.LDAPException, e:
            problem = str(e)
        except members.ChildFailed, e:
            problem = str(e)

        if problem:
            self.headtext.set_text("Failures Occured Adding User")
            self.midtext.set_text("The error was:\n%s\nThe account may be partially added "
                "and you may or may not be able to log in. Please contact systems committee." % problem)
            return
        else:
            self.headtext.set_text("User Added")
            self.midtext.set_text("Congratulations, %s has been added "
                "successfully. You should also rebuild the website in "
                "order to update the memberlist."
                % self.state['userid'])
