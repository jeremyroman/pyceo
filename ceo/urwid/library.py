import urwid
from ceo import members
from ceo.urwid import search
from ceo.urwid.widgets import *
from ceo.urwid.window import *
from sqlobject.sqlbuilder import *
from datetime import datetime

import ceo.library as lib



def library(data):
    menu = make_menu([
        ("Checkout Book", checkout_book, None),
        ("Return Book", return_book, None),
#        ("Search Books", search_books, None),
#        ("Add Book", add_book, None),
        ("Back", raise_back, None),
    ])
    push_window(menu, "Library")

def search_books(data):
    menu = make_menu([
        ("Overdue Books", overdue_books, None),
    ])
    push_window(menu, "Book Search")

def overdue_books(data):
    None

def checkout_book(data):
    push_wizard("Checkout", [CheckoutPage, BookSearchPage, ConfirmPage])

def return_book(data):
    push_wizard("Checkout", [CheckinPage, ConfirmPage])

class BookSearchPage(WizardPanel):
    def init_widgets(self):
        self.search = None
        self.state["book"] = None
        self.isbn = SingleEdit("ISBN: ")
        self.title = SingleEdit("Title: ")

        self.widgets = [
            urwid.Text("Book Search"),
            urwid.Text("(Only one field required.)"),
            urwid.Divider(),
            self.isbn,
            self.title
        ]

    def check(self):
        if self.state["book"] is None:
            push_window(SearchPage(self.isbn.get_edit_text(),
                                   self.title.get_edit_text(),
                                   None,
                                   self.state))
            return True
        else:
            return False
        

class CheckoutPage(WizardPanel):
    def init_widgets(self):
        self.state["user"] = "ERROR"
        self.state["task"] = "sign_out"
        self.user = SingleEdit("Username: ")
        
        self.widgets = [
            urwid.Text("Book Checkout"),
            urwid.Divider(),
            self.user,
        ]

    def check(self):
        self.state['user'] = self.user.get_edit_text()

class ConfirmPage(WizardPanel):
    def init_widgets(self):
        self.user = urwid.Text("Username: ")
        self.book = urwid.Text("Book: ")

        title = ""
        if self.state["task"] and self.state["task"]=="sign_in":
            title = "Checkin"
        else:
            title = "Checkout"

        self.widgets = [
            urwid.Text("Confirm " + title),
            urwid.Divider(),
            self.user,
            self.book
        ]

    def activate(self):
        self.user.set_text("Username: " + self.state["user"])
        if self.state["book"]:
            self.book.set_text("Book: " + self.state["book"].title)

    def check(self):
        #TODO: Validate user at some point (preferrably user entry screen)
        if self.state["task"] and self.state["task"]=="sign_in":
            self.state["book"].sign_in(self.state["user"])
        else:
            self.state["book"].sign_out(self.state["user"])
        pop_window()

        
class SearchPage(urwid.WidgetWrap):
    def __init__(self, isbn, title, user, state):
        self.state = state
        books = []
        widgets = []
        if not title is None and not title=="":
            books = lib.Book.select(LIKE(lib.Book.q.title, "%" + title + "%"))
        elif not isbn is None and not isbn=="":
            books = lib.Book.select(lib.Book.q.isbn==isbn)
        elif not user is None and not user=="":
            st = lib.Signout.select(AND(lib.Signout.q.username==user, lib.Signout.q.indate==None))
            for s in st:
                books.append(s.book)

        for b in books:
            widgets.append(urwid.AttrWrap(ButtonText(self.select, b, str(b)),
                                          None, 'selected'))
            widgets.append(urwid.Divider())

        urwid.WidgetWrap.__init__(self, urwid.ListBox(widgets))

    def select(self, book):
        self.state["book"] = book
        pop_window()

class CheckinPage(WizardPanel):
    def init_widgets(self):
        self.state["book"] = None
        self.state["user"] = "ERROR"
        self.state["task"] = "sign_in"
        self.user = SingleEdit("Username: ")
        
        self.widgets = [
            urwid.Text("Book Checkin"),
            urwid.Divider(),
            self.user,
        ]

    def check(self):
        if self.state["book"] is None:
            push_window(SearchPage(None,
                                   None,
                                   self.user.get_edit_text(),
                                   self.state))
            return True
        else:
            self.state["user"] = self.user.get_edit_text()
            return False
