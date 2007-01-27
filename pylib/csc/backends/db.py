# $Id: db.py 37 2006-12-28 10:00:50Z mspang $
"""
Database Backend Interface

This module is intended to be a thin wrapper around CEO database operations.
Methods on the connection class correspond in a straightforward way to SQL
queries. These methods may restructure and clean up query output but may make
no other assumptions about its content or purpose.

This module makes use of the PygreSQL Python bindings to libpq,
PostgreSQL's native C client library.
"""
import pgdb


class DBException(Exception):
    """Exception class for database-related errors."""
    pass
    
    
class DBConnection(object):
    """
    Connection to CEO's backend database. All database queries
    and updates are made via this class.
    
    Exceptions: (all methods)
        DBException - on database query failure

    Note: Updates will never take place until commit() is called.

    Note: In the event that any method of this class raises a
          DBException and that exception is caught, rollback()
          must be called before further queries will be successful.
    
    Example:
        connection = DBConnection()
        connection.connect("localhost", "ceo")
        
        # make queries and updates, i.e.
        connection.insert_member("Calum T. Dalek")
        
        connection.commit()
        connection.disconnect()
    """

    def __init__(self):
        self.cnx = None
        self.cursor = None

          
    def connect(self, hostname=None, database=None, username=None, password=None):
        """
        Establishes the connection to CEO's PostgreSQL database.
        
        Parameters:
            hostname - hostname:port to connect to
            database - name of database
            username - user to authenticate as
            password - password of username
        """

        if self.cnx: raise DBException("unable to connect: already connected")
        
        try:
            self.cnx = pgdb.connect(host=hostname, database=database,
                    user=username, password=password)
            self.cursor = self.cnx.cursor()
        except pgdb.Error, e:
            raise DBException("unable to connect: %s" % e)


    def disconnect(self):
        """Closes the connection to CEO's PostgreSQL database."""

        if self.cursor:
            self.cursor.close()
            self.cursor = None

        if self.cnx:
            self.cnx.close()
            self.cnx = None

    
    def connected(self):
        """Determine whether the connection has been established."""

        return self.cnx != None


    def commit(self):
        """Commits the current transaction and starts a new one."""

        self.cnx.commit()


    def rollback(self):
        """Aborts the current transaction."""

        self.cnx.rollback()



    ### Member-related methods ###
    
    def select_members(self, sql, params=None):
        """
        Retrieves a list CSC members selected by given SQL statement.
        
        This is a helper function that should generally not be called directly.
        
        Parameters:
            sql    - the SELECT sql statement
            params - parameters for the SQL statement

        The sql statement must select the six columns
        (memberid, name, studentid, program, type, userid)
        from the members table in that order.
        
        Returns: a memberid-keyed dictionary whose values are
                 column-keyed dictionaries with member attributes
        """
        
        # retrieve a list of all members
        try:
            self.cursor.execute(sql, params)
            members_list = self.cursor.fetchall()
        except pgdb.Error, e:
            raise DBException("SELECT statement failed: %s" % e)
        
        # build a dictionary of dictionaries from the result (a list of lists)
        members_dict = {}
        for member in members_list:
            memberid, name, studentid, program, type, userid = member
            members_dict[memberid] = {
                'memberid': member[0],
                'name': member[1],
                'studentid': member[2],
                'program': member[3],
                'type': member[4],
                'userid': member[5],
            }

        return members_dict


    def select_single_member(self, sql, params=None):
        """
        Retrieves a single member by memberid.

        This is a helper function that should generally not be called directly.
        
        See: self.select_members()

        Returns: a column-keyed dictionary with member attributes, or
                 None if no member matching member exists
        """

        # retrieve the member
        results = self.select_members(sql, params)

        # too many members returned
        if len(results) > 1:
            raise DBException("multiple members selected: sql='%s' params=%s" % (sql, repr(params)))

        # no such member
        elif len(results) < 1:
            return None

        # return the single match
        memberid = results.keys()[0]
        return results[memberid]

   
    def select_all_members(self):
        """
        Retrieves a list of all CSC members (past and present).

        See: self.select_members()
        
        Example: connection.select_all_members() -> {
                     0:    { 'memberid': 0, 'name': 'Calum T. Dalek' ...}
                     3349: { 'memberid': 3349, 'name': 'Michael Spang' ...}
                     ...
                 }
        """
        sql = "SELECT memberid, name, studentid, program, type, userid FROM members"
        return self.select_members(sql)
        
    
    def select_members_by_name(self, name_re):
        """
        Retrieves a list of all CSC members whose name matches name_re.
        
        See: self.select_members()
        
        Example: connection.select_members_by_name('Michael') -> {
                     3349: { 'memberid': 3349, 'name': 'Michael Spang' ...}
                     ...
                 }
        """
        sql = "SELECT memberid, name, studentid, program, type, userid FROM members WHERE name ~* %s"
        params = [ str(name_re) ]
     
        return self.select_members(sql, params)

    
    def select_members_by_term(self, term):
        """
        Retrieves a list of all CSC members who were members in the specified term.
        
        See: self.select_members()
        
        Example: connection.select_members_by_term('f2006') -> {
                     3349: { 'memberid': 3349, 'name': 'Michael Spang' ...}
                     ...
                 }
        """
        sql = "SELECT members.memberid, name, studentid, program, type, userid FROM members JOIN terms ON members.memberid=terms.memberid WHERE term=%s"
        params = [ str(term) ]
        
        return self.select_members(sql, params)

    
    def select_member_by_id(self, memberid):
        """
        Retrieves a single member by memberid.

        See: self.select_single_member()

        Example: connection.select_member_by_id(0) ->
                 { 'memberid': 0, 'name': 'Calum T. Dalek' ...}
        """
        sql = "SELECT memberid, name, studentid, program, type, userid FROM members WHERE memberid=%d"
        params = [ int(memberid) ]

        return self.select_single_member(sql, params)

    
    def select_member_by_account(self, username):
        """
        Retrieves a single member by UNIX account username.

        See: self.select_single_member()

        Example: connection.select_member_by_account('ctdalek') ->
                 { 'memberid': 0, 'name': 'Calum T. Dalek' ...}
        """
        sql = "SELECT memberid, name, studentid, program, type, userid FROM members WHERE userid=%s"
        params = [ username ]

        return self.select_single_member(sql, params)


    def select_member_by_studentid(self, studentid):
        """
        Retrieves a single member by student id number.

        See: self.select_single_member()

        Example: connection.select_member_by_studentid('nnnnnnnn') ->
                 { 'memberid': 3349, 'name': 'Michael Spang' ...}
        """
        sql = "SELECT memberid, name, studentid, program, type, userid FROM members WHERE studentid=%s"
        params = [ studentid ]

        return self.select_single_member(sql, params)

    
    def insert_member(self, name, studentid=None, program=None):
        """
        Creates a member with the specified attributes.

        Parameters:
            name      - full name of member
            studentid - student id number
            program   - program of study

        Example: connection.insert_member('Michael Spang', '99999999', 'Math/CS') -> 3349

        Returns: a memberid of created user
        """
        try:
            # retrieve the next memberid
            sql = "SELECT nextval('memberid_seq')"
            self.cursor.execute(sql)
            result = self.cursor.fetchone()
            memberid = result[0]
        
            # insert the member
            sql = "INSERT INTO members (memberid, name, studentid, program, type) VALUES (%d, %s, %s, %s, %s)"
            params = [ memberid, name, studentid, program, 'user' ]
            self.cursor.execute(sql, params)
            
            return memberid
        except pgdb.Error, e:
            raise DBException("failed to create member: %s" % e)

    
    def delete_member(self, memberid):
        """
        Deletes a member. Note that a member cannot
        be deleted until it has been unregistered from
        all terms.

        Parameters:
            memberid - the member id number to delete

        Example: connection.delete_member(3349)
        """
        sql = "DELETE FROM members WHERE memberid=%d"
        params = [ memberid ]

        try:
            self.cursor.execute(sql, params)
        except pgdb.Error, e:
            raise DBException("DELETE statement failed: %s" %e)

    
    def update_member(self, member):
        """
        Modifies member attributes.

        Parameters:
            member - a column-keyed dictionary with the new state of the member.
                     member['memberid'] must be present. ommitted columns
                     will not be changed. None is NULL.

        Returns: the full new state of the member as a column-keyed dictionary

        Example: connection.update_member({
                     'memberid': 3349,
                     'name': 'Michael C. Spang',
                     'program': 'CS!'
                 }) -> {
                     'memberid': 3349,
                     'name': 'Michael C. Spang',
                     'program': CS!',
                     'studentid': '99999999' # unchanged
                 }

        Equivalent Example:
                 member = connection.select_member_by_id(3349)
                 member['name'] = 'Michael C. Spang'
                 member['program'] = 'CS!'
                 connection.update_member(member) -> { see above }
        """
        try:
            
            # memberid to update
            memberid = member['memberid']
            
            # retrieve current state of member
            member_state = self.select_member_by_id(memberid)

            # build a list of changes to make
            changes = []
            for column in member.keys():
                if member[column] != member_state[column]:

                    # column's value must be updated
                    changes.append( (column, member[column]) )
                    member_state[column] = member[column]
            
            # no changes?
            if len(changes) < 1:
                return member_state
            
            # make the necessary changes in an update statement
            changes = zip(*changes)
            sql = "UPDATE members SET " + ", ".join(["%s=%%s"] * len(changes[0])) % changes[0] + " WHERE memberid=%d"
            params = changes[1] + ( memberid, )
            self.cursor.execute(sql, params)

            return member_state
        except pgdb.Error, e:
            raise DBException("member update failed: %s" % e)
        


    ### Term-related methods ###

    def select_term(self, memberid, term):
        """
        Determines whether a member is registered for a term.
        
        Parameters:
            memberid - the member id number
            term     - the term to check

        Returns: a matching term, or None

        Example: connection.select_term(3349, 'f2006') -> 'f2006'
        """
        sql = "SELECT term FROM terms WHERE memberid=%d AND term=%s"
        params = [ memberid, term ]

        # retrieve matches
        try:
            self.cursor.execute(sql, params)
            result = self.cursor.fetchall()
        except pgdb.Error, e:
            raise DBException("SELECT statement failed: %s" % e)

        if len(result) > 1:
            raise DBException("multiple rows in terms with memberid=%d term=%s" % (memberid, term))
        elif len(result) == 0:
            return None
        else:
            return result[0][0]


    def select_terms(self, memberid):
        """
        Retrieves a list of terms a member is registered for.

        Parameters:
            memberid - the member id number

        Returns: a sorted list of terms
        
        Example: connection.select_terms(3349) -> ['f2006']
        """
        sql = "SELECT term FROM terms WHERE memberid=%d"
        params = [ memberid ]

        # retrieve the list of terms
        try:
            self.cursor.execute(sql, params)
            result = self.cursor.fetchall()
        except pgdb.Error, e:
            raise DBException("SELECT statement failed: %s" % e)
        
        result = [ row[0] for row in result ]

        return result


    def insert_term(self, memberid, term):
        """
        Registers a member for a term.

        Parameters:
            memberid - the member id number to register
            term     - string representation of the term

        Example: connection.insert_term(3349, 'f2006')
        """
        sql = "INSERT INTO terms (memberid, term) VALUES (%d, %s)"
        params = [ memberid, term ]
        
        try:
            self.cursor.execute(sql, params)
        except pgdb.Error, e:
            raise DBException("INSERT statement failed: %s" % e)


    def delete_term(self, memberid, term):
        """
        Unregisters a member for a term.

        Parameters:
            memberid - the member id number to register
            term     - string representation of the term
        
        Example: connection.delete_term(3349, 'f2006')
        """
        sql = "DELETE FROM terms WHERE memberid=%d and term=%s"
        params = [ memberid, term ]

        try:
            self.cursor.execute(sql, params)
        except pgdb.Error, e:
            raise DBException("DELETE statement failed: %s" % e)

    
    def delete_term_all(self, memberid):
        """
        Unregisters a member for all registered terms.

        Parameters:
            memberid - the member id number to unregister
        
        Example: connection.delete_term_all(3349)
        """
        sql = "DELETE FROM terms WHERE memberid=%d"
        params = [ memberid ]
        
        # retrieve a list of terms
        try:
            self.cursor.execute(sql, params)
        except pgdb.Error, e:
            raise DBException("DELETE statement failed: %s" % e)


    ### Miscellaneous methods ###

    def trim_memberid_sequence(self):
        """
        Sets the value of the member id sequence to the id of the newest
        member. For use after extensive testing to prevent large
        intervals of unused memberids.

        Note: this does nothing unless the most recently added member(s) have been deleted
        """
        self.cursor.execute("SELECT setval('memberid_seq', (SELECT max(memberid) FROM members))")



### Tests ###

if __name__ == '__main__':
    HOST = "localhost"
    DATABASE = "ceo"

    connection = DBConnection()

    print "Running disconnect()"
    connection.disconnect()

    print "Running connect('%s', '%s')" % (HOST, DATABASE)
    connection.connect(HOST, DATABASE)

    print "Running select_all_members()", "->", len(connection.select_all_members()), "members"
    print "Running select_member_by_id(0)", "->", connection.select_member_by_id(0)['userid']
    print "Running select_members_by_name('Spang')", "->", connection.select_members_by_name('Spang').keys()
    print "Running select_members_by_term('f2006')", "->", "[" + ", ".join(map(str, connection.select_members_by_term('f2006').keys()[0:10])) + " ...]"
    
    print "Running insert_member('test_member', '99999999', 'program')",
    memberid = connection.insert_member('test_member', '99999999', 'program')
    print "->", memberid

    print "Running select_member_by_id(%d)" % memberid, "->", connection.select_member_by_id(memberid)
    print "Running insert_term(%d, 'f2006')" % memberid
    connection.insert_term(memberid, 'f2006')

    print "Running select_terms(%d)" % memberid, "->", connection.select_terms(memberid)
    print "Running update_member({'memberid':%d,'name':'test_updated','studentid':-1})" % memberid
    connection.update_member({'memberid':memberid,'name':'test_updated','studentid':99999999})
    print "Running select_member_by_id(%d)" % memberid, "->", connection.select_member_by_id(memberid)
   
    print "Running rollback()"
    connection.rollback()

    print "Resetting memberid sequence"
    connection.trim_memberid_sequence()
    
    print "Running disconnect()"
    connection.disconnect() 
