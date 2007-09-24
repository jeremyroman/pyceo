import random, time
import urwid, urwid.curses_display

from csc.apps.urwid.widgets import *
from csc.apps.urwid.window import *
import csc.apps.urwid.newmember as newmember
import csc.apps.urwid.renew as renew
import csc.apps.urwid.info as info
import csc.apps.urwid.search as search

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

def menu_items(items):
    return [ urwid.AttrWrap( ButtonText( cb, txt ), 'menu', 'selected') for (txt, cb) in items ]

def main_menu():
    menu = [
        ("New Member", new_member),
        ("Renew Membership", renew_member),
        ("Display Member", display_member),
        ("Search", search_members),
        ("Exit", raise_abort),
    ]

    listbox = urwid.ListBox( menu_items( menu ) )
    return listbox

def push_wizard(name, pages, dimensions=(50, 10)):
    state = {}
    wiz = Wizard()
    for page in pages:
        wiz.add_panel( page(state) )
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

def renew_member(*args, **kwargs):
    push_wizard("Renew Membership", [
        renew.IntroPage,
        renew.UserPage,
        renew.TermPage,
        renew.PayPage,
        renew.EndPage,
    ])

def display_member(a):
    push_wizard("Display Member", [
        renew.UserPage,
        info.InfoPage,
    ], (60, 15))

def search_members(a):
    menu = [
        ("Members by term", search_term),
        ("Members by name", search_name),
        ("Back", raise_back),
    ]

    listbox = urwid.ListBox( menu_items( menu ) )
    push_window(listbox, "Search")

def search_name(a):
    push_wizard("By Name", [ search.NamePage ])

def search_term(a):
    push_wizard("By Term", [ search.TermPage ])

def run():
    push_window( main_menu(), program_name() )
    event_loop( ui )

def start():
    ui.run_wrapper( run )

if __name__ == '__main__':
    start()
