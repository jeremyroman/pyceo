import urwid
from ceo import members
from ceo.urwid import search
from ceo.urwid.widgets import *
from ceo.urwid.window import *
from sqlobject.sqlbuilder import *
from datetime import datetime, timedelta
from ceo.pymazon import PyMazon

from ceo import terms

import ceo.library as lib

CONFIG_FILE = "/etc/csc/library.cf"

cfg = {}

def configure():
    """
    Load configuration
    """
    cfg_fields = [ "aws_account_key" ]
    temp_cfg = conf.read(CONFIG_FILE)
    conf.check_string_fields(CONFIG_FILE, cfg_fields, temp_cfg)
    cfg.update(temp_cfg)

def library(data):
    """
    Create the main menu for the library system.
    """
    menu = make_menu([
        ("Checkout Book", checkout_book, None),
        ("Return Book", return_book, None),
        ("Search Books", search_books, None),
#        ("Add Book", add_book, None),
        ("Back", raise_back, None),
    ])
    push_window(menu, "Library")

def search_books(data):
    """
    Define menus for searching books.
    """
    menu = make_menu([
        ("Overdue Books", overdue_books, None),
        ("Signed Out Books", outbooks_search, None),
    ])
    push_window(menu, "Book Search")

def add_book(data):
    """
    Add book to library.  Also stab Sapphyre.
    """
    push_wizard("Add Book", [BookAddPage])

def overdue_books(data):
    """
    Display a list of all books that are overdue.
    """
    oldest = datetime.today() - timedelta(weeks=2)
    overdue = lib.Signout.select(lib.Signout.q.outdate<oldest)

    widgets = []

    for s in overdue:
        widgets.append(urwid.AttrWrap(ButtonText(None, s.book, str(s.book)),
                                      None, 'selected'))
        widgets.append(urwid.Divider())
        
    push_window(urwid.ListBox(widgets))

    None

def outbooks_search(data):
    """
    Display a list of all books that are signed out.
    """
    overdue = lib.Signout.select(lib.Signout.q.indate==None)

    widgets = []

    for s in overdue:
        widgets.append(urwid.AttrWrap(ButtonText(None, s.book, str(s.book)),
                                      None, 'selected'))
        widgets.append(urwid.Divider())
        
    push_window(urwid.ListBox(widgets))

    None


def checkout_book(data):
    """
    Display the book checkout wizard.
    """
    push_wizard("Checkout", [CheckoutPage, BookSearchPage, ConfirmPage])

def return_book(data):
    """
    Display the book return wizard.
    """
    push_wizard("Checkout", [CheckinPage, ConfirmPage])

class BookAddPage(WizardPanel):
    """
    Thingy for going on screen to add books.
    """
    def init_widgets(self):
        """
        Make some widgets.
        """
        self.isbn = SingleEdit("ISBN: ")
        
        self.widgets = [
            urwid.Text("Adding New Book"),
            urwid.Divider(),
            self.isbn
        ]

    def check(self):
        """
        Do black magic.
        """
        isbn = self.isbn.get_edit_text()

        try:
            pymazon = PyMazon(cfg["aws_account_key"])
            book = pymazon.lookup(isbn)

            currents = lib.Book.select(lib.Book.q.isbn==isbn)
            if len(currents) == 0:
                lib.Book(isbn=isbn, title=book.title,
                         year=book.year, publisher=book.publisher)
            else:
                sys.stderr.write("Fuck you.\n")
                set_status("Book already exists, fucker.")
                
        except PyMazonError, e:
            sys.stderr.write("Book not added: " + e.message + "\n")
            set_status("Amazon thinks this is not a book.  Take it up with them.")
        

class BookSearchPage(WizardPanel):
    """
    The page used when searching for books.
    """
    def init_widgets(self):
        """
        Initialize the widgets and state variables.
        """
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
        """
        Validate input and update state.
        """
        if self.state["book"] is None:
            push_window(SearchPage(self.isbn.get_edit_text(),
                                   self.title.get_edit_text(),
                                   None,
                                   self.state))
            return True
        else:
            return False
        

class CheckoutPage(WizardPanel):
    """
    The initial page when checking out a book.
    """
    def init_widgets(self):
        """
        Initialize widgets and set up state.

        user -> the username to sign the book to
        task -> used for the confirmation dialog
        """
        self.state["user"] = "ERROR"
        self.state["task"] = "sign_out"
        self.user = LdapWordEdit(csclub_uri, csclub_base, 'uid', "Username: ")
        
        self.widgets = [
            urwid.Text("Book Checkout"),
            urwid.Divider(),
            self.user,
        ]

    def check(self):
        self.state['user'] = self.user.get_edit_text()
        if not members.registered(self.state['user'], terms.current()):
            set_status("User not registered for this term!")
            return True
        return False

class ConfirmPage(WizardPanel):
    """
    The confirmation screen when checking-in and checking-out
    a book.
    """
    def init_widgets(self):
        """
        Initialize widgets and state.

        task -> used to deterimine the action
        """
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
        """
        Ensures that correct data is displayed.
        """
        self.user.set_text("Username: " + self.state["user"])
        if self.state["book"]:
            self.book.set_text("Book: " + self.state["book"].title)

    def check(self):
        """
        Generally used for validation, but in this case it does
        the actual book check-out.
        """
        #TODO: Validate user at some point (preferrably user entry screen)
        if self.state["task"] and self.state["task"]=="sign_in":
            self.state["book"].sign_in(self.state["user"])
        else:
            self.state["book"].sign_out(self.state["user"])
        pop_window()

        
class SearchPage(urwid.WidgetWrap):
    """
    Displays search results.  Can search on isbn,
    title, or username (for books that are currently
    out).
    """
    def __init__(self, isbn, title, user, state):
        """
        This does the actual search, and sets up the screen
        when it's done.

        title -> search by (partial) title
        isbn -> search by (partial) isbn
        user -> search by username (for checked-out books)
        """
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
        """
        Marks a book for check-in or check-out.
        """
        self.state["book"] = book
        pop_window()

class CheckinPage(WizardPanel):
    """
    The initial page to start the check-in widget.
    """
    def init_widgets(self):
        """
        Throw some widgets on the screen and set up
        some state.

        book -> The book to check out.
        user -> Stupid people like books.
        task -> What are we doing?  (For confirm screen.)
        """
        self.state["book"] = None
        self.state["user"] = "ERROR"
        self.state["task"] = "sign_in"
        self.user = LdapWordEdit(csclub_uri, csclub_base, 'uid', "Username: ")
        
        self.widgets = [
            urwid.Text("Book Checkin"),
            urwid.Divider(),
            self.user,
        ]

    def check(self):
        """
        Pushes the search window.

        Should validate usernames.
        """
        if self.state["book"] is None:
            push_window(SearchPage(None,
                                   None,
                                   self.user.get_edit_text(),
                                   self.state))
            return True
        else:
            self.state["user"] = self.user.get_edit_text()
            return False
