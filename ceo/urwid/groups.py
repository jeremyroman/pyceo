import urwid
from ceo import members
from ceo.urwid import search
from ceo.urwid.widgets import *
from ceo.urwid.window import *

def change_group_member(data):
    push_wizard("%s %s Member" % (data["action"], data["name"]), [
        (ChangeMember, data),
        EndPage,
    ])

def list_group_members(data):
    mlist = members.list_group( data["group"] ).values()
    search.member_list( mlist )

def group_members(data):
    add_data = data.copy()
    add_data['action'] = 'Add'
    remove_data = data.copy()
    remove_data['action'] = 'Remove'
    menu = make_menu([
        ("Add %s member" % data["name"].lower(),
            change_group_member, add_data),
        ("Remove %s member" % data["name"].lower(),
            change_group_member, remove_data),
        ("List %s members" % data["name"].lower(), list_group_members, data),
        ("Back", raise_back, None),
    ])
    push_window(menu, "Manage %s" % data["name"])

class IntroPage(WizardPanel):
    def init_widgets(self):
        self.widgets = [
            urwid.Text( "Managing Club or Group" ),
            urwid.Divider(),
            urwid.Text( "Adding a member to a club will also grant them "
                        "access to the club's files and allow them to "
                        "become_club."
                        "\n\n")
        ]
    def focusable(self):
        return False

class InfoPage(WizardPanel):
    def init_widgets(self):
        self.group = LdapWordEdit(csclub_uri, csclub_base, 'uid',
            "Club or Group: ")
        self.widgets = [
            urwid.Text( "Club or Group Information"),
            urwid.Divider(),
            self.group,
        ]
    def check(self):
        group = self.group.get_edit_text()

        # check if group is valid
        if not group or not members.get_group(group):
            set_status("Group not found")
            self.focus_widget(self.group)
            return True

        data = {
            "name" : group,
            "group" : group,
            "groups" : [],
        }

        # Office Staff and Syscom get added to more groups
        if group == "syscom":
            data["name"] = "Systems Committee"
            data["groups"] = [ "office", "staff", "adm", "src" ]
        elif group == "office":
            data["name"] = "Office Staff"
            data["groups"] = [ "cdrom", "audio", "video", "www" ]

        group_members(data)

class ChangeMember(WizardPanel):
    def __init__(self, state, data):
        state['data'] = data
        WizardPanel.__init__(self, state)
    def init_widgets(self):
        self.userid = LdapWordEdit(csclub_uri, csclub_base, 'uid',
            "Username: ")

        data = self.state['data']
        self.widgets = [
            urwid.Text( "%s %s Member" % (data['action'], data['name']) ),
            urwid.Divider(),
            self.userid,
        ]
    def check(self):
        self.state['userid'] = self.userid.get_edit_text()
        if self.state['userid']:
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
        action = data['action'].lower()
        failed = []
        for group in data['groups'] + [data['group']]:
            try:
                members.change_group_member(action, group, self.state['userid'])
            except ldap.LDAPError:
                failed.append(group)
        if len(failed) == 0:
            self.headtext.set_text("%s succeeded" % data['action'])
            self.midtext.set_text("Congratulations, the group modification "
                "has succeeded.")
        else:
            self.headtext.set_text("%s Results" % data['action'])
            self.midtext.set_text("Failed to %s member to %s for the "
                "following groups: %s. This may indicate an attempt to add a "
                "duplicate group member or to delete a member that was not in "
                "the group." % (data['action'].lower(), data['name'],
                ', '.join(failed)))
