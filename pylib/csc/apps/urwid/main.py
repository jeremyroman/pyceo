import random, time, re
import urwid, urwid.curses_display

from csc.apps.urwid.widgets import *
from csc.apps.urwid.window import *
import csc.apps.urwid.newmember as newmember
import csc.apps.urwid.renew as renew
import csc.apps.urwid.info as info
import csc.apps.urwid.search as search
import csc.apps.urwid.positions as positions
import csc.apps.urwid.groups as groups

from csc.adm import accounts, members, terms
from csc.common.excep import InvalidArgument

ui = urwid.curses_display.Screen()

ui.register_palette([
    # name, foreground, background, mono
    ('banner', 'light gray', 'default', None),
    ('menu', 'light gray', 'default', 'bold'),
    ('selected', 'black', 'light gray', 'bold'),
])


def program_name():
    cwords = [ "CSC" ] * 20 + [ "Club" ] * 10 + [ "Campus" ] * 5 + \
        [ "Communist", "Canadian", "Celestial", "Cryptographic", "Calum's",
          "Canonical", "Capitalist", "Catastrophic", "Ceremonial", "Chaotic", "Civic",
          "City", "County", "Caffeinated" ]
    ewords = [ "Embellished", "Ergonomic", "Electric", "Eccentric", "European", "Economic",
        "Evil", "Egotistical", "Elliptic", "Emasculating", "Embalming",
        "Embryonic", "Emigrant", "Emissary's", "Emoting", "Employment", "Emulated",
        "Enabling", "Enamoring", "Encapsulated", "Enchanted", "Encoded", "Encrypted",
        "Encumbered", "Endemic", "Enhanced", "Enigmatic", "Enlightened", "Enormous",
        "Enrollment", "Enshrouded", "Ephermal", "Epidemic", "Episodic", "Epsilon",
        "Equitable", "Equestrian", "Equilateral", "Erroneous", "Erratic",
        "Espresso", "Essential", "Estate", "Esteemed", "Eternal", "Ethical", "Eucalyptus",
        "Euphemistic", "Envangelist", "Evasive", "Everyday", "Evidence", "Eviction", "Evildoer's",
        "Evolution", "Exacerbation", "Exalted", "Examiner's", "Excise", "Exciting", "Exclusion",
        "Exec", "Executioner's", "Exile", "Existential", "Expedient", "Expert", "Expletive",
        "Exploiter's", "Explosive", "Exponential", "Exposing", "Extortion", "Extraction",
        "Extraneous", "Extravaganza", "Extreme", "Extraterrestrial", "Extremist", "Eerie" ]
    owords = [ "Office" ] * 50 + [ "Outhouse", "Outpost" ]

    cword = random.choice(cwords)
    eword = random.choice(ewords)
    oword = random.choice(owords)

    return "%s %s %s" % (cword, eword, oword)

office_data = {
    "name" : "Office Staff",
    "group" : "office",
    "groups" : [ "office", "cdrom", "audio", "video", "www" ],
}

syscom_data = {
    "name" : "Systems Committee",
    "group" : "syscom",
    "groups" : [ "office", "staff", "adm", "src" ],
}

def menu_items(items):
    return [ urwid.AttrWrap( ButtonText( cb, data, txt ), 'menu', 'selected') for (txt, cb, data) in items ]

def main_menu():
    menu = [
        ("New Member", new_member, None),
        ("Renew Membership", renew_member, None),
        ("Create Club Account", new_club, None),
        ("Display Member", display_member, None),
        ("Search", search_members, None),
        ("Manage Positions", manage_positions, None),
        ("Manage Office Staff", group_members, office_data),
        ("Manage Systems Committee", group_members, syscom_data),
        ("Exit", raise_abort, None),
    ]

    listbox = urwid.ListBox( menu_items( menu ) )
    return listbox

def push_wizard(name, pages, dimensions=(50, 10)):
    state = {}
    wiz = Wizard()
    for page in pages:
        if type(page) != tuple:
            page = (page, )
        wiz.add_panel( page[0](state, *page[1:]) )
    push_window( urwid.Filler( urwid.Padding(
        urwid.LineBox(wiz), 'center', dimensions[0]),
        'middle', dimensions[1] ), name )

def new_member(*args, **kwargs):
    push_wizard("New Member", [
        newmember.IntroPage,
        newmember.InfoPage,
        newmember.SignPage,
        newmember.PassPage,
        newmember.EndPage,
    ])

def new_club(*args, **kwargs):
    push_wizard("New Club Account", [
        newmember.ClubIntroPage,
        newmember.ClubInfoPage,
        (newmember.EndPage, "club"),
    ], (60, 15))

def renew_member(*args, **kwargs):
    push_wizard("Renew Membership", [
        renew.IntroPage,
        renew.UserPage,
        renew.TermPage,
        renew.PayPage,
        renew.EndPage,
    ])

def display_member(data):
    push_wizard("Display Member", [
        renew.UserPage,
        info.InfoPage,
    ], (60, 15))

def search_members(data):
    menu = [
        ("Members by term", search_term, None),
        ("Members by name", search_name, None),
        ("Members by group", search_group, None),
        ("Back", raise_back, None),
    ]

    listbox = urwid.ListBox( menu_items( menu ) )
    push_window(listbox, "Search")

def search_name(data):
    push_wizard("By Name", [ search.NamePage ])

def search_term(data):
    push_wizard("By Term", [ search.TermPage ])

def search_group(data):
    push_wizard("By Group", [ search.GroupPage ])

def manage_positions(data):
    push_wizard("Manage Positions", [
        positions.IntroPage,
        positions.InfoPage,
        positions.EndPage,
    ], (50, 15))

def group_members(data):
    add_data = data.copy()
    add_data['type'] = 'Add'
    remove_data = data.copy()
    remove_data['type'] = 'Remove'
    menu = [
        ("Add %s member" % data["name"].lower(),
            change_group_member, add_data),
        ("Remove %s member" % data["name"].lower(),
            change_group_member, remove_data),
        ("List %s members" % data["name"].lower(), list_group_members, data),
        ("Back", raise_back, None),
    ]

    listbox = urwid.ListBox( menu_items( menu ) )
    push_window(listbox, "Manage %s" % data["name"])

def change_group_member(data):
    push_wizard("%s %s Member" % (data["type"], data["name"]), [
        (groups.ChangeMember, data),
        groups.EndPage,
    ])

def list_group_members(data):
    if not members.connected(): members.connect()
    mlist = members.list_group( data["group"] ).values()
    search.member_list( mlist )

def run():
    push_window( main_menu(), program_name() )
    event_loop( ui )

def start():
    ui.run_wrapper( run )

if __name__ == '__main__':
    start()
