import os, re, subprocess, ldap, socket
from ceo import conf, ldapi, terms, remote, ceo_pb2
from ceo.excep import InvalidArgument

class MySQLException(Exception):
    pass

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

