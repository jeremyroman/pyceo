import urwid
from ceo import members
from ceo.urwid import search
from ceo.urwid.widgets import *
from ceo.urwid.window import *

import ceo.library as lib

def library(data):
    menu = make_menu([
        ("Checkout Book", checkout_book, None),
        ("Return Book", return_book, None),
        ("List Books", search_books, None),
        ("Add Book", add_book, None),
        ("Remove Book", remove_book, None),
        ("Back", raise_back, None),
    ])
    push_window(menu, "Library")

def checkout_book(data):
    "should only search signed in books"
    pass

def return_book(data):
    "should bring up a searchbox of all the guys first"
    pass

def search_books(data):
    push_wizard("Search Books", [
        SearchPage,
    ])

def view_book(book):
    "this should develop into a full fledged useful panel for doing stuff with books. for now it's not."
    push_window(BookPage(book), "Book detail")

def view_books(books):
    #XXX should not use a hardcoded 20 in there, should grab the value from the width of the widget
    widgets = []
    for b in books:
        widgets.append(urwid.AttrWrap(ButtonText(view_book, b, str(b)), None, 'selected'))
        widgets.append(urwid.Divider())
    push_window(urwid.ListBox(widgets))

def add_book(data):
    push_wizard("Add Book", [AddBookPage])

def remove_book(data):
    pass



def parse_commaranges(s):
    """parse a string into a list of numbers"""
    def numbers(section):
        if "-" in section:
            range_ = section.split("-")
            assert len(range_) == 2
            start = int(range_[0])
            end = int(range_[1])
            return range(start, end+1) #+1 to be inclusive of end
        else:
            return [int(section)]
    
    l = []
    for y in s.split(","):
        l.append(numbers(y))
    return l


class AddBookPage(WizardPanel):
    def init_widgets(self):
        self.author = SingleEdit("Author: ")
        self.title = SingleEdit("Title: ")
        self.year = SingleIntEdit("Year(s): ")
        self.widgets = [
            urwid.Text("Add Book"),
            urwid.Divider(),
            self.author,
            self.title,
            self.year,
        ]
    
    def check(self):
        author = self.author.get_edit_text()
        if author == "":
            author = None #null it so that searching ignores
        title = self.title.get_edit_text()
        if title == "":
            title = None
        try:
            year = self.year.get_edit_text()
            if year == "":
                year = None
            else:
                year = int(year)
        except:
            self.focus_widget(self.year)
            set_status("Invalid year")
            return True
        lib.add(author, title, year)
        raise_back()


   
class SearchPage(WizardPanel):
    def init_widgets(self):
        self.author = SingleEdit("Author: ")
        self.title = SingleEdit("Title: ")
        self.year = SingleEdit("Year(s): ")
        self.signedout = urwid.CheckBox("Checked Out: ")
        self.widgets = [
            urwid.Text("Search Library"),
            urwid.Divider(),
            self.author,
            self.title,
            self.year,
            urwid.Divider(),
            urwid.Text("Author/Title are regexes.\nYear is a comma-separated list or a hyphen-separated range")
        ]
    def check(self):
        author = self.author.get_edit_text()
        if author == "":
            author = None #null it so that searching ignores
        title = self.title.get_edit_text()
        if title == "":
            title = None
        try:
            years = self.year.get_edit_text()
            if years == "":
                years = None
            else:
                #try to parse the year field
                years = parse_commaranges( year )
        except:
            self.focus_widget(self.year)
            set_status("Invalid year")
            return True
        signedout = self.signedout.get_state()
        view_books(lib.search(author, title, years, signedout)) 




class CheckoutPage(urwid.WidgetWrap):
    def __init__(self, book):
        self.book = SingleEdit("Book: ") #this needs to be a widget that when you click on it, it takes you to the search_books pane, lets you pick a book, and then drops you back here
        self.user = SingleEdit("Checkoutee: ")
        self.widgets = [
            urwid.Text("Checkout A Book"),
            urwid.Divider(),
            self.book,
            self.user,
        ]
        urwid.WidgetWrap.__init__(self, urwid.Pile(self.widgets))

class ConfirmDialog(urwid.WidgetWrap):
    def __init__(self, msg):
        raise NotImplementedError

def Confirm(msg):
    #this should be in widgets.py
    push_window(ConfirmDialog(msg))

class InputDialog(urwid.WidgetWrap):
    def __init__(self, msg=None):
        msg = urwid.Text(msg)
        self.input = SingleEdit("")
        ok = urwid.Button("OK", self.ok)
        cancel = urwid.Button("Cancel", self.cancel)
        buttons = urwid.Columns([ok, cancel])
        display = urwid.Pile([msg, self.input, buttons])
        urwid.WidgetWrap.__init__(self, display)
    def ok():
        self.result = self.input.get_edit_text()
        raise Abort() #break out of the inner event loop
    def cancel():
        self.result = None
        raise Abort()

def urwid_input(msg):
    #this should be in widgets.py
    dialog = InputDialog(msg)
    push_window(dialog)
    event_loop(urwid.main.ui) #HACK
    return dialog.result

def do_checkout(book):
    "this is temporary to fil lthe gap until we see what we reall need"
    username = urwid_input("Username to check out to?")
    if username is None:
        set_status("Checkout cancelled")
    else:
        book.sign_out(username)

def do_delete(book):
    if Confirm("Do you wish to delete %r?" % book):
        lib.delete(book)

class BookPage(urwid.WidgetWrap):
    def __init__(self, book):
        self._book = book
        self.author = SingleEdit("Author: ")
        self.title = SingleEdit("Title: ")
        self.year = SingleIntEdit("Year: ")
        #now need a checkout widget to go down here..
        #and "Delete"
        if book.signout is None:
            self.checkout = ButtonText(do_checkout, book, "Check Out")
        else:
            self.checkout = ButtonText(lambda book: book.sign_in(), book, "Check In")
        #self.remove = ButtonText(do_delete, book, "Delete")
        display = urwid.GridFlow([self.author, self.title, self.year,
                                  #self.checkout,
                                  #self.remove
                                  ], 15, 3, 1, 'left')
        urwid.WidgetWrap.__init__(self, self.author)

