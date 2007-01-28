"""
Database Backend Interface

This module is intended to be a thin wrapper around CEO database operations.
Methods on the connection class correspond in a straightforward way to SQL
queries. These methods may restructure and clean up query output but may make
no other assumptions about its content or purpose.

This module makes use of the PyGreSQL Python bindings to libpq,
PostgreSQL's native C client library.
"""
import pgdb


class DBException(Exception):
    """Exception class for database-related errors."""
    pass
    
    
class DBConnection(object):
    """
    A connection to CEO's backend database. All database queries
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

        return self.cnx is not None


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
            members_dict[member[0]] = {
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

    
    def select_member_by_userid(self, username):
        """
        Retrieves a single member by UNIX account username.

        See: self.select_single_member()

        Example: connection.select_member_by_userid('ctdalek') ->
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

    
    def insert_member(self, name, studentid=None, program=None, mtype='user', userid=None):
        """
        Creates a member with the specified attributes.

        Parameters:
            name      - full name of member
            studentid - student id number
            program   - program of study
            mtype     - member type
            userid    - account id

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
            sql = "INSERT INTO members (memberid, name, studentid, program, type, userid) VALUES (%d, %s, %s, %s, %s, %s)"
            params = [ memberid, name, studentid, program, mtype, userid ]
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
        member. For use after testing to prevent large intervals of unused
        memberids from developing.

        Note: this does nothing unless the most recently added member(s) have been deleted
        """
        self.cursor.execute("SELECT setval('memberid_seq', (SELECT max(memberid) FROM members))")



### Tests ###

if __name__ == '__main__':

    from csc.common.test import *
 
    conffile = "/etc/csc/pgsql.cf"

    cfg = dict([map(str.strip, a.split("=", 1)) for a in map(str.strip, open(conffile).read().split("\n")) if "=" in a ])
    hostnm = cfg['server'][1:-1]
    dbase = cfg['database'][1:-1]

    # t=test m=member s=student d=default e=expected u=updated
    tmname = 'Test Member'
    tmuname = 'Member Test'
    tmsid = '00000004'
    tmusid = '00000008'
    tmprogram = 'Undecidable'
    tmuprogram = 'Nondetermined'
    tmtype = 'Untyped'
    tmutype = 'Poly'
    tmuserid = 'tmem'
    tmuuserid = 'identifier'
    tm2name = 'Test Member 2'
    tm2sid = '00000005'
    tm2program = 'Undeclared'
    tm3name = 'T. M. 3'
    dtype = 'user'
    tmterm = 'w0000'
    tm3term = 'f1112'
    tm3term2 = 's1010'

    emdict = { 'name': tmname, 'program': tmprogram, 'studentid': tmsid, 'type': tmtype, 'userid': tmuserid }
    emudict = { 'name': tmuname, 'program': tmuprogram, 'studentid': tmusid, 'type': tmutype, 'userid': tmuuserid }
    em2dict = { 'name': tm2name, 'program': tm2program, 'studentid': tm2sid, 'type': dtype, 'userid': None }
    em3dict = { 'name': tm3name, 'program': None, 'studentid': None, 'type': dtype, 'userid': None }
    
    test(DBConnection)
    connection = DBConnection()
    success()

    test(connection.connect)
    connection.connect(hostnm, dbase)
    success()

    test(connection.connected)
    assert_equal(True, connection.connected())
    success()

    test(connection.insert_member)
    tmid = connection.insert_member(tmname, tmsid, tmprogram, tmtype, tmuserid)
    tm2id = connection.insert_member(tm2name, tm2sid, tm2program)
    tm3id = connection.insert_member(tm3name)
    assert_equal(True, int(tmid) >= 0)
    assert_equal(True, int(tmid) >= 0)
    success()

    emdict['memberid'] = tmid
    emudict['memberid'] = tmid
    em2dict['memberid'] = tm2id
    em3dict['memberid'] = tm3id

    test(connection.select_member_by_id)
    m1 = connection.select_member_by_id(tmid)
    m2 = connection.select_member_by_id(tm2id)
    m3 = connection.select_member_by_id(tm3id)
    assert_equal(emdict, m1)
    assert_equal(em2dict, m2) 
    assert_equal(em3dict, m3)
    success()

    test(connection.select_all_members)
    members = connection.select_all_members()
    assert_equal(True, tmid in members)
    assert_equal(True, tm2id in members)
    assert_equal(True, tm3id in members)
    assert_equal(emdict, members[tmid])
    success()

    test(connection.select_members_by_name)
    members = connection.select_members_by_name(tmname)
    assert_equal(True, tmid in members)
    assert_equal(False, tm3id in members)
    assert_equal(emdict, members[tmid])
    success()

    test(connection.select_member_by_userid)
    assert_equal(emdict, connection.select_member_by_userid(tmuserid))
    success()

    test(connection.insert_term)
    connection.insert_term(tmid, tmterm)
    connection.insert_term(tm3id, tm3term)
    connection.insert_term(tm3id, tm3term2)
    success()

    test(connection.select_members_by_term)
    members = connection.select_members_by_term(tmterm)
    assert_equal(True, tmid in members)
    assert_equal(False, tm2id in members)
    assert_equal(False, tm3id in members)
    success()

    test(connection.select_term)
    assert_equal(tmterm, connection.select_term(tmid, tmterm))
    assert_equal(None, connection.select_term(tm2id, tmterm))
    assert_equal(tm3term, connection.select_term(tm3id, tm3term))
    assert_equal(tm3term2, connection.select_term(tm3id, tm3term2))
    success()

    test(connection.select_terms)
    trms = connection.select_terms(tmid)
    trms2 = connection.select_terms(tm2id)
    assert_equal([tmterm], trms)
    assert_equal([], trms2)
    success()

    test(connection.delete_term)
    assert_equal(tm3term, connection.select_term(tm3id, tm3term))
    connection.delete_term(tm3id, tm3term)
    assert_equal(None, connection.select_term(tm3id, tm3term))
    success()

    test(connection.update_member)
    connection.update_member({'memberid': tmid, 'name': tmuname})
    connection.update_member({'memberid': tmid, 'program': tmuprogram, 'studentid': tmusid })
    connection.update_member({'memberid': tmid, 'userid': tmuuserid, 'type': tmutype })
    assert_equal(emudict, connection.select_member_by_id(tmid))
    connection.update_member(emdict)
    assert_equal(emdict, connection.select_member_by_id(tmid))
    success()

    test(connection.delete_term_all)
    connection.delete_term_all(tm2id)
    connection.delete_term_all(tm3id)
    assert_equal([], connection.select_terms(tm2id))
    assert_equal([], connection.select_terms(tm3id))
    success()

    test(connection.delete_member)
    connection.delete_member(tm3id)
    assert_equal(None, connection.select_member_by_id(tm3id))
    negative(connection.delete_member, (tmid,), DBException, "delete of term-registered member")
    success()

    test(connection.rollback)
    connection.rollback()
    assert_equal(None, connection.select_member_by_id(tm2id))
    success()

    test(connection.commit)
    connection.commit()
    success()

    test(connection.trim_memberid_sequence)
    connection.trim_memberid_sequence()
    success()

    test(connection.disconnect)
    connection.disconnect()
    assert_equal(False, connection.connected())
    connection.disconnect()
    success()
