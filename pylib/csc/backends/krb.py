"""
Kerberos Backend Interface

This module is intended to be a thin wrapper around Kerberos operations.
Methods on the connection object correspond in a straightforward way to
calls to the Kerberos Master server.

A Kerberos principal is the second half of a CSC UNIX account. The principal
stores the user's password and and is used for all authentication on CSC
systems. Accounts that do not authenticate (e.g. club accounts) do not need
a Kerberos principal.

Unfortunately, there are no Python bindings to libkadm at this time. As a
temporary workaround, this module communicates with the kadmin CLI interface
via a pseudo-terminal and a pipe.
"""
import os
import ipc


class KrbException(Exception):
    """Exception class for all Kerberos-related errors."""
    pass


class KrbConnection(object):
    """
    Connection to the Kerberos master server (kadmind). All Kerberos
    principal updates are made via this class.

    Exceptions: (all methods)
        KrbException - on query/update failure

    Example:
        connection = KrbConnection()
        connection.connect(...)

        # make queries and updates, e.g.
        connection.delete_principal("mspang")

        connection.disconnect()
    """

    def __init__(self):
        self.pid = None
    

    def connect(self, principal, keytab):
        """
        Establishes the connection to the Kerberos master server.

        Parameters:
            principal - the Kerberos princiapl to authenticate as
            keytab    - keytab filename for authentication

        Example: connection.connect('ceo/admin@CSCLUB.UWATERLOO.CA', '/etc/ceo.keytab')
        """

        # check keytab
        if not os.access(keytab, os.R_OK):
            raise KrbException("cannot access Kerberos keytab: %s" % keytab)
        
        # command to run
        kadmin = '/usr/sbin/kadmin'
        kadmin_args = ['kadmin', '-p', principal, '-kt', keytab]
        
        # fork the kadmin command
        self.pid, self.kadm_out, self.kadm_in = ipc.popeni(kadmin, kadmin_args)
        
        # read welcome messages
        welcome = self.read_result()
        
        # sanity checks on welcome messages
        for line in welcome:
            
            # ignore auth message
            if line.find("Authenticating") == 0:
                continue

            # ignore log file message
            elif line.find("kadmin.log") != -1:
                continue

            # error message?
            else:
                raise KrbException("unexpected kadmin output: " + welcome[0])
    
    
    def disconnect(self):
        """Close the connection to the master server."""
        
        if self.pid:
            
            # close the pipe connected to kadmin's standard input
            self.kadm_in.close()
            
            # close the master pty connected to kadmin's stdout
            try:
                self.kadm_out.close()
            except OSError:
                pass

            # wait for kadmin to terminate
            os.waitpid(self.pid, 0)
            self.pid = None


    def connected(self):
        """Determine whether the connection has been established."""

        return self.pid is not None



    ### Helper Methods ###
    
    def read_result(self):
        """
        Helper function to read output of kadmin until it
        prompts for input.

        Returns: a list of lines returned by kadmin
        """

        # list of lines output by kadmin
        result = []
        lines = []

        # the kadmin prompt that signals the end output
        # note: KADMIN_ARGS[0] must be "kadmin" or the actual prompt will differ
        prompt = "kadmin:"

        # timeout variables. the timeout will start at timeout and
        # increase up to max_timeout when read() returns nothing (i.e., times out)
        timeout = 0.01
        timeout_increment = 0.10
        timeout_maximum = 1.00
        
        # input loop: read from kadmin until the kadmin prompt
        buf = ''
        while True:
            
            # attempt to read any available data
            data = self.kadm_out.read(block=False, timeout=timeout)
            buf += data

            # nothing was read
            if data == '':
                
                # so wait longer for data next time
                if timeout < timeout_maximum:
                    timeout += timeout_increment
                    continue

                # give up after too much waiting
                else:

                    # check kadmin status
                    status = os.waitpid(self.pid, os.WNOHANG)
                    if status[0] == 0:

                        # kadmin still alive
                        raise KrbException("timeout while reading response from kadmin")

                    else:

                        # kadmin died!
                        raise KrbException("kadmin died while reading response:\n%s\n%s" % ("\n".join(lines), buf))

            # break into lines and save all but the final
            # line (which is incomplete) into result
            lines = buf.split("\n")
            buf = lines[-1]
            lines = lines[:-1]
            for line in lines:
                line = line.strip()
                result.append(line)
           
            # if the incomplete line in the buffer is the kadmin prompt,
            # then the result is complete and may be returned
            if buf.strip() == prompt:
                break

        return result
    
    
    def execute(self, command):
        """
        Helper function to execute a kadmin command.

        Parameters:
            command - command string to pass on to kadmin
        
        Returns: a list of lines output by the command
        """
        
        # there should be no remaining output from the previous
        # command. if there is then something is broken.
        stale_output = self.kadm_out.read(block=False, timeout=0)
        if stale_output != '':
            raise KrbException("unexpected kadmin output: " + stale_output)
        
        # send the command to kadmin
        self.kadm_in.write(command + "\n")
        self.kadm_in.flush()
        
        # read the command output and return it
        result = self.read_result()
        return result
    

    
    ### Commands ###
    
    def list_principals(self):
        """
        Retrieve a list of Kerberos principals.

        Returns: a list of principals

        Example: connection.list_principals() -> [
                     "ceo/admin@CSCLUB.UWATERLOO.CA",
                     "sysadmin/admin@CSCLUB.UWATERLOO.CA",
                     "mspang@CSCLUB.UWATERLOO.CA",
                     ...
                 ]
        """
        
        principals = self.execute("list_principals")

        # assuming that there at least some host principals
        if len(principals) < 1:
            raise KrbException("no kerberos principals")

        # detect error message
        if principals[0].find("kadmin:") == 0:
            raise KrbException("list_principals returned error: " + principals[0])

        # verify principals are well-formed
        for principal in principals:
            if principal.find("@") == -1:
                raise KrbException('malformed pricipal: "' + principal + '"')

        return principals
    
    
    def get_principal(self, principal):
        """
        Retrieve principal details.

        Returns: a dictionary of principal attributes

        Example: connection.get_principal("ceo/admin@CSCLUB.UWATERLOO.CA") -> {
                     "Principal": "ceo/admin@CSCLUB.UWATERLOO.CA",
                     "Policy": "[none]",
                     ...
                 }
        """
        
        output = self.execute('get_principal "' + principal + '"')
        
        # detect error message
        if output[0].find("kadmin:") == 0:
            raise KrbException("get_principal returned error: " + output[0])

        # detect more errors
        if output[0].find("get_principal: ") == 0:
            
            message = output[0][15:]
            
            # principal does not exist => None
            if message.find("Principal does not exist") == 0:
                return None

        # dictionary to store attributes
        principal_attributes = {}

        # attributes that will not be returned
        ignore_attributes = ['Key']

        # split output into a dictionary of attributes
        for line in output:
            key, value = line.split(":", 1)
            value = value.strip()
            if not key in ignore_attributes:
                principal_attributes[key] = value
                
        return principal_attributes
    
    
    def get_privs(self):
        """
        Retrieve privileges of the current principal.
        
        Returns: a list of privileges

        Example: connection.get_privs() ->
                     [ "GET", "ADD", "MODIFY", "DELETE" ]
        """
        
        output = self.execute("get_privs")

        # one line of output is expected
        if len(output) > 1:
            raise KrbException("unexpected output of get_privs: " + output[1])

        # detect error message
        if output[0].find("kadmin:") == 0:
            raise KrbException("get_privs returned error: " + output[0])

        # parse output by removing the prefix and splitting it around spaces
        if output[0][:20] != "current privileges: ":
            raise KrbException("malformed get_privs output: " + output[0])
        privs = output[0][20:].split(" ")

        return privs
    
    
    def add_principal(self, principal, password):
        """
        Create a new principal.

        Parameters:
            principal - the name of the principal
            password  - the principal's initial password
        
        Example: connection.add_principal("mspang@CSCLUB.UWATERLOO.CA", "opensesame")
        """

        # exec the add_principal command
        if password.find('"') == -1:
            self.kadm_in.write('add_principal -pw "' + password + '" "' + principal + '"\n')
            
        # fools at MIT didn't bother implementing escaping, so passwords
        # that contain double quotes must be treated specially
        else:
            self.kadm_in.write('add_principal "' + principal + '"\n')
            self.kadm_in.write(password + "\n" + password + "\n")

        # send request and read response
        self.kadm_in.flush()
        output = self.read_result()

        # verify output
        created = False
        for line in output:

            # ignore NOTICE lines
            if line.find("NOTICE:") == 0:
                continue

            # ignore prompts
            elif line.find("Enter password") == 0 or line.find("Re-enter password") == 0:
                continue

            # record whether success message was encountered
            elif line.find("Principal") == 0 and line.find("created.") != 0:
                created = True

            # error messages
            elif line.find("add_principal:") == 0 or line.find("kadmin:") == 0:
                
                # principal exists
                if line.find("already exists") != -1:
                    raise KrbException("principal already exists")

                # misc errors
                else:
                    raise KrbException(line)

            # unknown output
            else:
                raise KrbException("unexpected add_principal output: " + line)
           
        # ensure success message was received
        if not created:
            raise KrbException("kadmin did not acknowledge principal creation")
    
    
    def delete_principal(self, principal):
        """
        Delete a principal.

        Example: connection.delete_principal("mspang@CSCLUB.UWATERLOO.CA")
        """
        
        # exec the delete_principal command and read response
        self.kadm_in.write('delete_principal -force "' + principal + '"\n')
        self.kadm_in.flush()
        output = self.read_result()

        # verify output
        deleted = False
        for line in output:

            # ignore reminder
            if line.find("Make sure that") == 0:
                continue

            # record whether success message was encountered
            elif line.find("Principal") == 0 and line.find("deleted.") != -1:
                deleted = True

            # error messages
            elif line.find("delete_principal:") == 0 or line.find("kadmin:") == 0:
                
                # principal exists
                if line.find("does not exist") != -1:
                    raise KrbException("principal does not exist")

                # misc errors
                else:
                    raise KrbException(line)

            # unknown output
            else:
                raise KrbException("unexpected delete_principal output: " + line)
           
        # ensure success message was received
        if not deleted:
            raise KrbException("did not receive principal deleted")
        

    def change_password(self, principal, password):
        """
        Changes a principal's password.

        Example: connection.change_password("mspang@CSCLUB.UWATERLOO.CA", "opensesame")
        """

        # exec the add_principal command
        if password.find('"') == -1:
            self.kadm_in.write('change_password -pw "' + password + '" "' + principal + '"\n')
        else:
            self.kadm_in.write('change_password "' + principal + '"\n')
            self.kadm_in.write(password + "\n" + password + "\n")

        # send request and read response
        self.kadm_in.flush()
        output = self.read_result()

        # verify output
        changed = False
        for line in output:

            # ignore NOTICE lines
            if line.find("NOTICE:") == 0:
                continue

            # ignore prompts
            elif line.find("Enter password") == 0 or line.find("Re-enter password") == 0:
                continue

            # record whether success message was encountered
            elif line.find("Password") == 0 and line.find("changed.") != 0:
                changed = True

            # error messages
            elif line.find("change_password:") == 0 or line.find("kadmin:") == 0:
                raise KrbException(line)

            # unknown output
            else:
                raise KrbException("unexpected change_password output: " + line)
           
        # ensure success message was received
        if not changed:
            raise KrbException("kadmin did not acknowledge password change")



### Tests ###

if __name__ == '__main__':

    from csc.common.test import *
    import random

    conffile = '/etc/csc/kerberos.cf'

    cfg = dict([map(str.strip, a.split("=", 1)) for a in map(str.strip, open(conffile).read().split("\n")) if "=" in a ])
    principal = cfg['admin_principal'][1:-1]
    keytab = cfg['admin_keytab'][1:-1]
    realm = cfg['realm'][1:-1]

    # t=test p=principal e=expected
    tpname = 'testpirate' + '@' + realm
    tpw = str(random.randint(10**30, 10**31-1)) + 'YAR!'
    eprivs = ['GET', 'ADD', 'MODIFY', 'DELETE']

    test(KrbConnection)
    connection = KrbConnection()
    success()

    test(connection.connect)
    connection.connect(principal, keytab)
    success()

    try:
        connection.delete_principal(tpname)
    except KrbException:
        pass

    test(connection.connected)
    assert_equal(True, connection.connected())
    success()

    test(connection.add_principal)
    connection.add_principal(tpname, tpw)
    success()

    test(connection.list_principals)
    pals = connection.list_principals()
    assert_equal(True, tpname in pals)
    success()

    test(connection.get_privs)
    privs = connection.get_privs()
    assert_equal(eprivs, privs)
    success()

    test(connection.get_principal)
    princ = connection.get_principal(tpname)
    assert_equal(tpname, princ['Principal'])
    success()

    test(connection.delete_principal)
    connection.delete_principal(tpname)
    assert_equal(None, connection.get_principal(tpname))
    success()

    test(connection.disconnect)
    connection.disconnect()
    assert_equal(False, connection.connected())
    success()

