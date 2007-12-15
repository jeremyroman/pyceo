import sys, random, ldap, urwid.curses_display
from ceo import members, ldapi
from ceo.urwid.widgets import *
from ceo.urwid.window import *
from ceo.urwid import newmember, renew, info, search, positions, groups

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
        "Enrollment", "Enshrouded", "Ephemeral", "Epidemic", "Episodic", "Epsilon",
        "Equitable", "Equestrian", "Equilateral", "Erroneous", "Erratic",
        "Espresso", "Essential", "Estate", "Esteemed", "Eternal", "Ethical", "Eucalyptus",
        "Euphemistic", "Evangelist", "Evasive", "Everyday", "Evidence", "Eviction", "Evildoer's",
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
        ("Manage Club or Group Members", manage_group, None),
        ("Manage Positions", manage_positions, None),
        ("Manage Office Staff", groups.group_members, office_data),
        ("Manage Systems Committee", groups.group_members, syscom_data),
        ("Exit", raise_abort, None),
    ]

    listbox = urwid.ListBox( menu_items( menu ) )
    return listbox

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

def manage_group(*args, **kwargs):
    push_wizard("Manage Club or Group Members", [
        groups.IntroPage,
        groups.InfoPage,
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

def run():
    push_window( main_menu(), program_name() )
    event_loop( ui )

def start():
    try:
        print "Connecting...",
        sys.stdout.flush()
        members.connect()
        print "done."

        ui.run_wrapper( run )
    except ldap.LOCAL_ERROR, e:
        print ldapi.format_ldaperror(e)
        print "Hint: You may need to run 'kinit'"
    except ldap.INSUFFICIENT_ACCESS, e:
        print ldapi.format_ldaperror(e)
        print "You probably aren't permitted to do whatever you just tried."
        print "Admittedly, ceo probably shouldn't have crashed either."

if __name__ == '__main__':
    start()
