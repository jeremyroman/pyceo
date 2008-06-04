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
        ("Search Books", search_books, None),
        ("Add Book", add_book, None),
        #("Remove Book", remove_book, None),
        ("Back", raise_back, None),
    ])
    push_window(menu, "Library")

def checkout_book(data):
    "should only search signed in books"
    view_books(lib.search(signedout=False))

def return_book(data):
    "should bring up a searchbox of all the guys first"
    view_books(lib.search(signedout=True))

def search_books(data):
    push_window(urwid.Filler(SearchPage(), valign='top'), "Search Books")

def view_book(book):
    "this should develop into a full fledged useful panel for doing stuff with books. for now it's not."
    push_window(urwid.Filler(BookPage(book), valign='top'), "Book detail")

def view_books(books):
    #XXX should not use a hardcoded 20 in there, should grab the value from the width of the widget
    #TODO: this should take the search arguments, and stash them away, and everytime you come back to this page it should refresh itself
    widgets = []
    for b in books:
        widgets.append(urwid.AttrWrap(ButtonText(view_book, b, str(b)), None, 'selected'))
        widgets.append(urwid.Divider())
    push_window(urwid.ListBox(widgets))

def add_book(data):
    push_wizard("Add Book", [AddBookPage])

#def remove_book(data):
#    pass


def parse_commaranges(s):
    """parse a string into a list of numbers"""
    """Fixme: this should be in a different module"""
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
        l.extend(numbers(y))
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


   
class SearchPage(urwid.WidgetWrap):
    """
    TODO: need to be able to jump to "search" button quickly; perhaps trap a certain keypress?
    """
    def __init__(self):
        self.author = SingleEdit("Author: ")
        self.title = SingleEdit("Title: ")
        self.year = SingleEdit("Year(s): ")
        self.ISBN = SingleEdit("ISBN: ")
        self.description = urwid.Edit("Description: ", multiline=True)
        self.signedout = urwid.CheckBox(": Checked Out")
        self.ok = urwid.Button("Search", self.search)
        self.back = urwid.Button("Back", raise_back)
        widgets = [
            #urwid.Text("Search Library"),
            #urwid.Divider(),
            self.author,
            self.title,
            self.year,
            self.ISBN,
            self.description,
            self.signedout,
            urwid.Divider(),
            urwid.Text("String fields are regexes.\nYear is a comma-separated list or a hyphen-separated range")
        ]
        buttons = urwid.GridFlow([self.ok, self.back], 10, 3, 1, align='right')
        urwid.WidgetWrap.__init__(self, urwid.Pile([urwid.Pile(widgets), buttons]))        
        
    def search(self, *sender):
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
                years = parse_commaranges( years )
        except:
            raise
            self.focus_widget(self.year)
            set_status("Invalid year")
            return True
        ISBN = self.ISBN.get_edit_text()
        if ISBN == "": ISBN = None
        description = self.description.get_edit_text()
        if description == "": description = None
        signedout = self.signedout.get_state()
        view_books(lib.search(author, title, years, ISBN, description, signedout)) 



#DONTUSE
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

#DONTUSE
class ConfirmDialog(urwid.WidgetWrap):
    def __init__(self, msg):
        raise NotImplementedError

#DONTUSE
def Confirm(msg):
    #this should be in widgets.py
    push_window(ConfirmDialog(msg))

#DONTUSE
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

#DONTUSE
def urwid_input(msg):
    #this should be in widgets.py
    dialog = InputDialog(msg)
    push_window(dialog)
    event_loop(urwid.main.ui) #HACK
    return dialog.result


def do_delete(book):
    if Confirm("Do you wish to delete %r?" % book):
        lib.delete(book)

class BookPageBase(urwid.WidgetWrap):
    def __init__(self):
        self.author = SingleEdit("Author: ")
        self.title = SingleEdit("Title: ")
        self.year = SingleIntEdit("Year: ")
        self.ISBN = urwid.Text("ISBN: ")
        self.description = urwid.Edit("Description: ", multiline=True)

        buttons = urwid.GridFlow(self._init_buttons(), 13, 2, 1, 'center') 
        display = urwid.Pile([self.author, self.title, self.year, self.ISBN, self.description,] +
                                self._init_widgets() +
                                [urwid.Divider(), buttons])
        urwid.WidgetWrap.__init__(self, display)
        self.refresh()

    def _init_widgets(self):
        return []
    def _init_buttons(self):
        return []
    def refresh(self, *sender):
        """update the widgets from the data model"""
        self.author.set_edit_text(self._book.author)
        self.title.set_edit_text(self._book.title)
        self.year.set_edit_text(str(self._book.year))
        self.ISBN.set_text("ISBN: " + self._book.ISBN)
        self.description.set_edit_text(self._book.description)


class BookPage(BookPageBase):
    def __init__(self, book):
        self._book = book
        BookPageBase.__init__(self)
    def _init_widgets(self):
        self.checkout_label = urwid.Text("") 
        return [self.checkout_label]
    def _init_buttons(self):
        save = urwid.Button("Save", self.save)
        self.checkout_button = urwid.Button("", self.checkout)
        back = urwid.Button("Back", raise_back)
        remove = urwid.Button("Delete", self.delete)
        return [back, self.checkout_button, save, remove]
        
    #all these *senders are to allow these to be used as event handlers or just on their own
    def refresh(self, *sender):
        BookPageBase.refresh(self, *sender)
        if self._book.signout is None:
            self.checkout_label.set_text("Checked In")
            self.checkout_button.set_label("Check Out")
        else:
            self.checkout_label.set_text(self._book.signout)
            self.checkout_button.set_label("Check In")
        
    def save(self, *sender):
        self._book.author = self.author.get_edit_text()
        self._book.title = self.title.get_edit_text()
        yeartmp = self.year.get_edit_text()
        if yeartmp is not None: yeartmp = int(yeartmp)
        self._book.year = yeartmp
        #self._book.ISBN = .... #no... don't do this...
        self._book.description = self.description.get_edit_text()
        lib.save(self._book)
        self.refresh()
    
    def checkout(self, *sender):
        username = "nguenthe"
        self._book.sign_out(username)
        self.save()
    
    def checkin(self, *sender):
        self._book.sign_in()
        self.save()
    
    def delete(self, *sender):
        lib.delete(self._book)
        raise_back()
