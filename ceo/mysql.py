import os, re, subprocess, ldap, socket, pwd
from ceo import conf, ldapi, terms, remote, ceo_pb2
from ceo.excep import InvalidArgument

class MySQLException(Exception):
    pass

def write_mysql_info(username, password):
    homedir = pwd.getpwnam(username).pw_dir
    password_file = '%s/ceo-mysql-info' % homedir
    if os.path.exists(password_file):
        os.rename(password_file, password_file + '.old')
    fd = os.open(password_file, os.O_CREAT|os.O_EXCL|os.O_WRONLY, 0660)
    fh = os.fdopen(fd, 'w')
    fh.write("""MySQL Database Information for %(username)s

Your new MySQL database was created. To connect, use
the following options:

Database: %(username)s
Username: %(username)s
Password: %(password)s
Hostname: localhost

The command to connect using the MySQL command-line client is

  mysql %(username)s -u %(username)s -p

This database is only accessible from caffeine.
""" % { 'username': username, 'password': password })

    fh.close()

def create_mysql(username):
    try:
        request = ceo_pb2.AddMySQLUser()
        request.username = username

        out = remote.run_remote('mysql', request.SerializeToString())

        response = ceo_pb2.AddMySQLUserResponse()
        response.ParseFromString(out)

        if any(message.status != 0 for message in response.messages):
            raise MySQLException('\n'.join(message.message for message in response.messages))

        return response.password
    except remote.RemoteException, e:
        raise MySQLException(e)

