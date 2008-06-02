""" The backend for the library-tracking system

This uses shelve which is pretty simplistic, but which should be sufficient for our (extremely minimal) use of the library.

There is a booklist (book=(Author, Title, Year, Signout)) where signout is None for "Checked In" or a (userid, date) to give who and when that book was signed out.
"""

import shelve
import time
import re

LIBRARY_DB = "./csc_library.db"

class Book:
    def __init__(self, author, title, year):
        """Any of these may be None to indicate 'unknown'."""
        self.author =author
        self.title = title
        self.year = year
        self.signout = None
    def sign_out(self, username):
        if self.signout is None:
            self.signout = Signout(username)
        else:
            raise Exception("Book already signed out to %s" % self.signout.name, b)
    def sign_in(self): 
        if self.signout is not None:
            self.signout = None
        else:
            raise Exception("Book was not signed out, no need to sign it in")
    
    def __str__(self):
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
    shelve.open(LIBRARY_DB,'n').close()


def add(author, title, year):
    db = shelve.open(LIBRARY_DB,'w') #use w here (not c) to ensure a crash if the DB file got erased (is this a good idea?)
    i = len(db)
    db[str(i)] = Book(author, title, year)
    db.close()

def search(author=None, title=None, year=None):
    """search for a title
    author and title are regular expressions
    year is a single number or a list of numbers (so use range() to search the DB)
    whichever ones passed in that aren't None are the restrictions used in the search
    possibly-useful side effect of this design is that search() just gets the list of everything
    this is extraordinarily inefficient, but whatever (I don't think that without having an indexer run inthe background we can improve this any?)
    returns: a list of Book objects
    """
    db = shelve.open(LIBRARY_DB, 'w', writeback=True) #open it for writing so that changes to books get saved
    all = db.values() #this should pull out the ID numbers somehow too.. bah
    if author is not None:
       all = [book for book in all if book.author and re.match(author, book.author)] #should factor this out 
    if title is not None:
       all = [book for book in all if book.title and re.match(title, book.title)] #should factor this out 
    if year is not None:
        if type(year) == int:
            year = [year]
        #now assume year is a list
        all = [book for book in all if book.year and book.year in year]
    db.close()
    return all


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
