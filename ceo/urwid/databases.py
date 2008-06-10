import urwid
from ceo import members
from ceo.urwid import search
from ceo.urwid.widgets import *
from ceo.urwid.window import *

def databases(menu):
    menu = make_menu([
        ("Create MySQL database", create_mysql_db, None),
        ("Back", raise_back, None),
    ])
    push_window(menu, "Databases")

def create_mysql_db(data):
    pass
