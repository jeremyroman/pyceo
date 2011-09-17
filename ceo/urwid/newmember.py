import ldap, urwid #, re
from ceo import members, terms, remote, uwldap
from ceo.urwid.widgets import *
from ceo.urwid.window import *

class IntroPage(WizardPanel):
    def init_widgets(self):
        self.widgets = [
            urwid.Text( "Joining the Computer Science Club" ),
            urwid.Divider(),
            urwid.Text( "CSC membership is $2.00 per term. Please ensure "
                        "the fee is deposited into the safe before continuing." ),
        ]
    def focusable(self):
        return False

class ClubIntroPage(WizardPanel):
    def init_widgets(self):
        self.widgets = [
            urwid.Text( "Club Accounts" ),
            urwid.Divider(),
            urwid.Text( "We provide other UW clubs accounts for email and "
                        "web hosting, free of charge. Like members, clubs "
                        "get web hosting at %s. We can also arrange for "
                        "uwaterloo.ca subdomains; please instruct the club "
                        "representative to contact the systems committee "
                        "for more information. Club accounts do not have "
                        "passwords, and exist primarily to own club data. "
                        % "http://csclub.uwaterloo.ca/~clubid/" ),
        ]
    def focusable(self):
        return False

class ClubUserIntroPage(WizardPanel):
    def init_widgets(self):
        self.widgets = [
            urwid.Text( "Club Rep Account" ),
            urwid.Divider(),
            urwid.Text( "This is for people who need access to a club account, "
                        "but are not currently interested in full CSC membership. "
                        "Registering a user in this way grants one term of free "
                        "access to our machines, without any other membership "
                        "privileges (they can't vote, hold office, etc). If such "
                        "a user later decides to join, use the Renew Membership "
                        "option." ),
        ]
    def focusable(self):
        return False

class InfoPage(WizardPanel):
    def init_widgets(self):
        self.name = SingleEdit("Full name: ")
        self.program = SingleEdit("Program of Study: ")
     	self.email = SingleEdit("Email: ")
	self.userid = LdapFilterWordEdit(uwldap.uri(), uwldap.base(), 'uid',
            {'cn':self.name, 'ou':self.program}, "Username: ")
        self.widgets = [
            urwid.Text( "Member Information" ),
            urwid.Divider(),
            self.userid,
            self.name,
            self.program,
            self.email,
            urwid.Divider(),
            urwid.Text("Notes:"),
            urwid.Text("- Make sure to check ID (watcard, drivers license)"),
            urwid.Text("- Make sure to use UW userids for current students\n  (we check uwldap to see if you are a full member)"),
        ]
    def check(self):
        self.state['userid'] = self.userid.get_edit_text()
        self.state['name'] = self.name.get_edit_text()
        self.state['program'] = self.program.get_edit_text()
	self.state['email'] = self.email.get_edit_text()
        if len( self.state['userid'] ) < 3:
            self.focus_widget( self.userid )
            set_status("Username is too short")
            return True
        elif len( self.state['name'] ) < 4:
            self.focus_widget( self.name )
            set_status("Name is too short")
            return True
        elif self.state['userid'] == self.state['name']:
            self.focus_widget(self.name)
            set_status("Name matches username")
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
        elif self.state['userid'] == self.state['name']:
            self.focus_widget(self.name)
            set_status("Name matches username")
            return True
        clear_status()

class NumberOfTermsPage(WizardPanel):
    def init_widgets(self):
        self.count = SingleIntEdit("Count: ")
        self.widgets = [
            urwid.Text("Number of Terms"),
            urwid.Divider(),
            urwid.Text("The member will be initially registered for this many "
                       "consecutive terms.\n"),
            self.count
        ]
    
    def activate(self):
        self.count.set_edit_text("1")
        self.focus_widget(self.count)
    
    def check(self):
        self.state['terms'] = terms.interval(terms.current(), self.count.value())
        
        if len(self.state['terms']) == 0:
            self.focus_widget(self.count)
            set_status("Registering for zero terms?")
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
        self.headtext.set_text("Adding %s" % self.state['userid'])
        self.midtext.set_text("Please be patient while the user is added. "
                              "If more than a few seconds pass, check for a "
                              "phase variance and try inverting the polarity.")
        set_status("Contacting the gibson...")

        redraw()

        problem = None
        try:
            if self.utype == 'member':
                members.create_member(
                        self.state['userid'],
                        self.state['password'],
                        self.state['name'],
                        self.state['program'],
                        self.state['email'])
                members.register(self.state['userid'], self.state['terms'])

                mailman_result = members.subscribe_to_mailing_list(self.state['userid'])
                if mailman_result.split(': ',1)[0] not in ('Subscribed', 'Already a member', 'Disabled'):
                    problem = mailman_result

            elif self.utype == 'clubuser':
                members.create_member(
                        self.state['userid'],
                        self.state['password'],
                        self.state['name'],
                        self.state['program'],
                        self.state['email'],
                        club_rep=True)
                members.register_nonmember(self.state['userid'], self.state['terms'])
            elif self.utype == 'club':
                members.create_club(self.state['userid'], self.state['name'])
            else:
                raise Exception("Internal Error")
        except members.InvalidArgument, e:
            problem = str(e)
        except ldap.LDAPError, e:
            problem = str(e)
        except members.MemberException, e:
            problem = str(e)
        except remote.RemoteException, e:
            problem = str(e)

        clear_status()

        if problem:
            self.headtext.set_text("Failures Occured Adding User")
            self.midtext.set_text("The error was:\n\n%s\n\nThe account may be partially added "
                "and you may or may not be able to log in. Or perhaps you are not office staff. "
                "If this was not expected please contact systems committee." % problem)
            return
        else:
            set_status("Strombola Delivers")
            self.headtext.set_text("User Added")
            self.midtext.set_text("Congratulations, %s has been added "
                "successfully. You should also rebuild the website in "
                "order to update the memberlist."
                % self.state['userid'])
