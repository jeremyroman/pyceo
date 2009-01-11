from sqlobject import *
from sqlobject.sqlbuilder import *
from ceo import conf
import time
from datetime import datetime, timedelta

CONFIG_FILE = "etc/library.cf"

cfg = {}

def configure():
    """ Load configuration
    """
    cfg_fields = [ "library_connect_string" ]
    
    temp_cfg = conf.read(CONFIG_FILE)
    conf.check_string_fields(CONFIG_FILE, cfg_fields, temp_cfg)
    cfg.update(temp_cfg)
    
    sqlhub.processConnection = connectionForURI(cfg["library_connect_string"])

class Book(SQLObject):
    isbn = StringCol()
    title = StringCol()
    description = StringCol()
    year = StringCol()
    publisher = StringCol()
    authors = SQLRelatedJoin("Author")
    signouts = SQLMultipleJoin("Signout")

    def sign_out(self, u):
        s = Signout(username=u, book=self,
                    outdate=datetime.today(), indate=None)

    def sign_in(self, u):
        s = self.signouts.filter(AND(Signout.q.indate==None, Signout.q.username==u))
        if s.count() > 0:
            s.orderBy(Signout.q.outdate).limit(1).getOne(None).sign_in()
            return True
        else:
            raise Exception("PEBKAC:  Book not signed out!")

    def __str__(self):
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
    name = StringCol()
    books = RelatedJoin("Book")

class Signout(SQLObject):
    username = StringCol()
    book = ForeignKey("Book")
    outdate = DateCol()
    indate = DateCol()

#     def __init__(self, u, b, o, i):
#         username = u
#         book = b
#         outdate = o
#         indate = i

    def sign_in(self):
        self.indate = datetime.today()

    def _get_due_date(self):
        """
        Compute the due date of the book based on the sign-out
        date.
        """
        return self.outdate + timedelta(weeks=2)

if __name__ == "__main__":
    configure()
    Book.createTable()
    Author.createTable()
    Signout.createTable()
    print "This functionality isn't implemented yet."
