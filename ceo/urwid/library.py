import urwid
from ceo import members
from ceo.urwid import search
from ceo.urwid.widgets import *
from ceo.urwid.window import *

def library(data):
    menu = make_menu([
        ("Checkout Book", checkout_book, None),
        ("Return Book", return_book, None),
        ("Search Books", search_books, None),
        ("Add Book", add_book, None),
        ("Remove Book", remove_book, None),
        ("Back", raise_back, None),
    ])
    push_window(menu, "Library")

def checkout_book(data):
    pass

def return_book(data):
    pass

def search_books(data):
    pass

def add_book(data):
    pass

def remove_book(data):
    pass
