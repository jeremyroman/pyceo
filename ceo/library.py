from sqlobject import *
from sqlobject.sqlbuilder import *
from ceo import conf
from ceo import members
from ceo import terms
import time
from datetime import datetime, timedelta

CONFIG_FILE = "/etc/csc/library.cf"

cfg = {}

def configure():
    """
    Load configuration
    """
    cfg_fields = [ "library_connect_string" ]
    
    temp_cfg = conf.read(CONFIG_FILE)
    conf.check_string_fields(CONFIG_FILE, cfg_fields, temp_cfg)
    cfg.update(temp_cfg)
    
    sqlhub.processConnection = connectionForURI(cfg["library_connect_string"])

class Book(SQLObject):
    """
    A book.  This does all the stuff we could
    ever want to do with a book.
    """
    isbn = StringCol()
    title = StringCol()
    year = StringCol()
    publisher = StringCol()
    authors = SQLRelatedJoin("Author")
    signouts = SQLMultipleJoin("Signout")

    def sign_out(self, u):
        """
        Call this with a username to sign out
        a book.
        """
        if members.registered(u,terms.currrent()):
            s = Signout(username=u, book=self,
                        outdate=datetime.today(), indate=None)

    def sign_in(self, u):
        """
        Call this to check a book back in to
        the library.  Username is used to
        disambiguate in case more than one
        copy of this book has been signed out.
        """
        s = self.signouts.filter(AND(Signout.q.indate==None, Signout.q.username==u))
        if s.count() > 0:
            s.orderBy(Signout.q.outdate).limit(1).getOne(None).sign_in()
            return True
        else:
            raise Exception("PEBKAC:  Book not signed out!")

    def __str__(self):
        """
        Magic drugs to make books display
        nicely.
        """
        book = "%s [%s]" % (self.title, self.year)
        book += "\nBy: "
        for a in self.authors:
            book += a.name
            book += ", "

        if self.authors.count() < 1:
            book += "(unknown)"

        book = book.strip(", ")

        signouts = self.signouts.filter(Signout.q.indate==None)
        if signouts.count() > 0:
            book += "\nSigned Out: "
            for s in signouts:
                book += s.username + ", "

        book = book.strip(", ")
        
        return book


class Author(SQLObject):
    """
    An author can author many books, and a book
    can have many authors.  This lets us map
    both ways.
    """
    name = StringCol()
    books = RelatedJoin("Book")

class Signout(SQLObject):
    """
    An instance of a signout associates usernames,
    books, signout dates, and return dates to mark
    that a book has been signed out by a particular
    user.
    """
    username = StringCol()
    book = ForeignKey("Book")
    outdate = DateCol()
    indate = DateCol()

    def sign_in(self):
        """
        Terminate the signout (return the book).
        """
        self.indate = datetime.today()

    def _get_due_date(self):
        """
        Compute the due date of the book based on the sign-out
        date.
        """
        return self.outdate + timedelta(weeks=2)

if __name__ == "__main__":
    print "This functionality isn't implemented yet."
