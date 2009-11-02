from ceo import members, terms, mysql

class MySQL:
  help = '''
mysql create <username>

Creates a mysql database for a user.
'''
  def main(self, args):
    if len(args) != 2 or args[0] != 'create':
        print self.help
        return
    username = args[1]
    problem = None
    try:
        password = mysql.create_mysql(username)

        try:
            mysql.write_mysql_info(username, password)
            helpfiletext = "Settings written to ~%s/ceo-mysql-info." % username
        except (KeyError, IOError, OSError), e:
            helpfiletext = "An error occured writing the settings file: %s" % e

        print "MySQL database created"
        print ("Connection Information: \n"
               "\n"
               "Database: %s\n"
               "Username: %s\n"
               "Hostname: localhost\n"
               "Password: %s\n"
               "\n"
               "%s\n"
               % (username, username, password, helpfiletext))
    except mysql.MySQLException, e:
        print "Failed to create MySQL database"
        print
        print "We failed to create the database. The error was:\n\n%s" % e

