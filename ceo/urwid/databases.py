import urwid
from ceo import members, mysql
from ceo.urwid import search
from ceo.urwid.widgets import *
from ceo.urwid.window import *

class IntroPage(WizardPanel):
    def init_widgets(self):
        self.widgets = [
            urwid.Text("MySQL databases"),
            urwid.Divider(),
            urwid.Text("Members and hosted clubs may have one MySQL database each. You may "
                       "create a database for an account if: \n"
                       "\n"
                       "- It is your personal account,\n"
                       "- It is a club account, and you are in the club group, or\n"
                       "- You are on the CSC systems committee\n"
                       "\n"
                       "You may also use this to reset your database password."
                       )
        ]
    def focusable(self):
        return False

class UserPage(WizardPanel):
    def init_widgets(self):
        self.userid = LdapWordEdit(csclub_uri, csclub_base, 'uid',
            "Username: ")

        self.widgets = [
            urwid.Text("Member Information"),
            urwid.Divider(),
            urwid.Text("Enter the user which will own the new database."),
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
            password = mysql.create_mysql(self.state['userid'])
            self.headtext.set_text("MySQL database created")
            self.midtext.set_text("Connection Information: \n"
                                  "\n"
                                  "Database: %s\n"
                                  "Username: %s\n"
                                  "Hostname: localhost\n"
                                  "Password: %s\n"
                                  "\n"
                                  "Note: Databases are only accessible from caffeine\n"
                                  % (self.state['userid'], self.state['userid'], password))
        except mysql.MySQLException, e:
            self.headtext.set_text("Failed to create MySQL database")
            self.midtext.set_text("We failed to create the database. The error was:\n\n%s" % e)

    def check(self):
        pop_window()
