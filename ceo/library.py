""" The backend for the library-tracking system

This uses shelve which is pretty simplistic, but which should be sufficient for our (extremely minimal) use of the library.

There is a booklist (book=(Author, Title, Year, Signout)) where signout is None for "Checked In" or a (userid, date) to give who and when that book was signed out.

We key books by their ISBN number (this is currently only hoboily implemented; we don't use real ISBNs yet)

Future plans: use barcode scanners, index by ISBN, cross reference to library of congress
Future plans: keep a whole stack of people who have checked it out (the last few at least)
"""

import shelve
import time
import re
from ceo import conf

### Configuration ###

CONFIG_FILE = '/etc/csc/library.cf'

cfg = {}

def configure():
    """Load Members Configuration"""

    string_fields = [ 'library_db_path' ]
    numeric_fields = [ ]

    # read configuration file
    cfg_tmp = conf.read(CONFIG_FILE)

    # verify configuration
    conf.check_string_fields(CONFIG_FILE, string_fields, cfg_tmp)
    conf.check_integer_fields(CONFIG_FILE, numeric_fields, cfg_tmp)

    # update the current configuration with the loaded values
    cfg.update(cfg_tmp)



def format_maybe(v):
    """little hack to make printing things that may come out as None nicer"""
    if v is None:
        return "unknown"
    else:
        return str(v)

class Book:
    def __init__(self, author, title, year, ISBN=None, description=""):
        """Any of these may be None to indicate 'unknown'."""
        self.author = author
        self.title = title
        self.year = year
        self.ISBN = ISBN
        self.description = description
        self.signout = None
    def sign_out(self, username):
        if self.signout is None:
            self.signout = Signout(username)
        else:
            raise Exception("Book already signed out to %s" % self.signout.name, self)
    def sign_in(self): 
        if self.signout is not None:
            self.signout = None
        else:
            raise Exception("Book was not signed out, no need to sign it in")
    
    def __str__(self):
        author = self.author
        book = "%s [%s]\nBy: %s" % (format_maybe(self.title), format_maybe(self.year), format_maybe(self.author))
        if self.signout:
            book += "\n Signed out by %s on %s" %  (self.signout.name, time.ctime(self.signout.date))
        return book
    
    def __repr__(self):
        return "Book(author=%r, title=%r, year=%r, signout=%r)" % (self.author, self.title, self.year, self.signout)

class Signout:
    """Represents a sign-out of a book to someone. Automatically records when the signout occured"""
    def __init__(self, name):
        #in theory we could check that the name given to us is in LDAP
        self.name = str(name)
        self.date = time.time()
    def __repr__(self):
        return "Signout(%r, %s)" % (self.name, time.ctime(self.date))







def reset():
    """make a fresh database"""
    shelve.open(cfg['library_db_path'],'n').close()


def add(author, title, year):
    db = shelve.open(cfg['library_db_path'],'c') #use w here (not c) to ensure a crash if the DB file got erased (is this a good idea?)
    isbn = str(len(db)) #not true, but works for now
    db[isbn] = Book(author, title, year, isbn)
    db.close()

def search(author=None, title=None, year=None, ISBN=None, description=None, signedout=None):
    """search for a title
    author and title are regular expressions
    year is a single number or a list of numbers (so use range() to search the DB)
    whichever ones passed in that aren't None are the restrictions used in the search
    possibly-useful side effect of this design is that search() just gets the list of everything
    this is extraordinarily inefficient, but whatever (I don't think that without having an indexer run inthe background we can improve this any?)
    returns: a sequence of Book objects
    """
    db = shelve.open(cfg['library_db_path'], 'c', writeback=True) #open it for writing so that changes to books get saved
    if type(year) == int:
        year = [year]
    def filter(book):
        """filter by the given params, but only apply those that are non-None"""
        #this code is SOOO bad, someone who has a clear head please fix this
        #we need to apply:
        b_auth = b_title = b_year = b_ISBN = b_description = b_signedout = True #default to true (in case of None i.e. this doesn't apply) 
        if author is not None:
            if re.search(author, book.author):
                b_auth = True
            else:
                b_auth = False
        if title is not None:
            if re.search(title, book.title): #should factor this out 
                b_title = True
            else:
                b_title = False
        if year is not None: #assume year is a list
            if book.year in year:
                b_year = True
            else:
                b_year = False
        if ISBN is not None:
            if re.search(ISBN, book.ISBN):
                b_ISBN = True
            else:
                b_ISBN = False
        if description is not None:
            if re.search(description, book.description):
                b_description = True
            else:
                b_description = False
        if signedout is not None:
            b_signedout = signedout == (book.signout is not None)
        return b_auth and b_title and b_year and b_ISBN and b_description and b_signedout
    
    for i in db:
        book = db[i]
        if(filter(book)):
            yield book
    db.close()


def save(book):
    db = shelve.open(cfg['library_db_path'], "w")
    assert book.ISBN is not None, "We should really handle this case better, like making an ISBN or something"
    db[book.ISBN] = book
    db.close()

def delete(book):
    db = shelve.open(cfg['library_db_path'], "w")
    del db[book.ISBN]
    

#def delete(....):
#    """must think about how to do this one; it'll have to be tied to the DB ID somehow"""
#    pass

if __name__ == '__main__':
    #print "Making database"
    #reset()
    #print
    #print "Filling database"
    #add("Bob McBob", "My Life Of Crime", None)
    print
    print "Listing database"
    for b in search():
        #b.sign_out("nguenthe")
        print b 
