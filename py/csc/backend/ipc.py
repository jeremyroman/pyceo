# $Id: ipc.py 26 2006-12-20 21:25:08Z mspang $
"""
IPC Library Functions

This module contains very UNIX-specific code to allow interactive
communication with another program. For CEO they are required to
talk to kadmin because there is no Kerberos administration Python
module. Real bindings to libkadm5 are doable and thus a TODO.
"""
import os, pty, select


class _pty_file(object):
    """
    A 'file'-like wrapper class for pseudoterminal file descriptors.
    
    This wrapper is necessary because Python has a nasty
    habit of throwing OSError at pty EOF.
      
    This class also implements timeouts for read operations
    which are handy for avoiding deadlock when both
    processes are blocked in a read().
      
    See the Python documentation of the file class
    for explanation of the methods.
    """
    def __init__(self, fd):
        self.fd = fd
        self.buffer = ''
        self.closed = False
    def __repr__(self):
        status='open'
        if self.closed:
            status = 'closed'
        return "<" + status + " pty '" + os.ttyname(self.fd) + "'>"
    def read(self, size=-1, block=True, timeout=0.1):
        if self.closed: raise ValueError
        if size < 0:
            data = None

            # read data, catching OSError as EOF
            try:
                while data != '':
                
                    # wait timeout for the pty to become ready, otherwise stop reading
                    if not block and len(select.select([self.fd],[],[], timeout)[0]) == 0:
                       break
                       
                    data = os.read(self.fd, 65536)
                    self.buffer += data
            except OSError:
                pass
            
            data = self.buffer
            self.buffer = ''
            return data
        else:
            if len(self.buffer) < size:

                # read data, catching OSError as EOF
                try:
                    
                    # wait timeout for the pty to become ready, then read
                    if block or len(select.select([self.fd],[],[], timeout)[0]) != 0:
                        self.buffer += os.read(self.fd, size - len(self.buffer) )
                    
                except OSError:
                    pass

            data = self.buffer[:size]
            self.buffer = self.buffer[size:]
            return data
    def readline(self, size=-1, block=True, timeout=0.1):
        data = None

        # read data, catching OSError as EOF
        try:
            while data != '' and self.buffer.find("\n") == -1 and (size < 0 or len(self.buffer) < size):

                # wait timeout for the pty to become ready, otherwise stop reading
                if not block and len(select.select([self.fd],[],[], timeout)[0]) == 0:
                   break
                 
                data = os.read(self.fd, 128)
                self.buffer += data
        except OSError:
            pass
            
        split_index = self.buffer.find("\n") + 1
        if split_index < 0:
            split_index = len(self.buffer)
        if size >= 0 and split_index > size:
            split_index = size
        line = self.buffer[:split_index]
        self.buffer = self.buffer[split_index:]
        return line
    def readlines(self, sizehint=None, block=True, timeout=0.1):
        lines = []
        line = None
        while True:
            line = self.readline(-1, False, timeout)
            if line == '': break
            lines.append(line)
        return lines
    def write(self, data):
        if self.closed: raise ValueError
        os.write(self.fd, data)
    def writelines(self, lines):
        for line in lines:
            self.write(line)
    def __iter__(self):
        return self
    def next(self):
        line = self.readline()
        if line == '':
            raise StopIteration
        return line
    def isatty(self):
        if self.closed: raise ValueError
        return os.isatty(self.fd)
    def fileno(self):
        if self.closed: raise ValueError
        return self.fd
    def flush(self):
        if self.closed: raise ValueError
        os.fsync(self.fd)
    def close(self):
        if not self.closed: os.close(self.fd)
        self.closed = True
            

def popeni(command, args, env=None):
    """
    Open an interactive session with another command.

    Parameters:
        command - the command to run (full path)
        args    - a list of arguments to pass to command
        env     - optional environment for command

    Returns: (pid, stdout, stdIn)
    """
    
    # use a pipe to send data to the child
    child_stdin, parent_stdin = os.pipe()

    # a pipe for receiving data would cause buffering and
    # is therefore not suitable for interactive communication
    # i.e. parent_stdout, child_stdout = os.pipe()

    # therefore a pty must be used instead
    master, slave = pty.openpty()
 
    # collect both stdout and stderr on the pty
    parent_stdout, child_stdout = master, slave
    parent_stderr, child_stderr = master, slave

    # fork the child to communicate with
    pid = os.fork()

    # child process
    if pid == 0:
     
        # close all of the parent's fds
        os.close(parent_stdin)
        if parent_stdout != parent_stdin:
            os.close(parent_stdout)
        if parent_stderr != parent_stdin and parent_stderr != parent_stdout:
            os.close(parent_stderr)
    
        # if stdout is a terminal, set it to the controlling terminal
        if os.isatty(child_stdout):

            # determine the filename of the tty
            tty = os.ttyname(child_stdout)
        
            # create a new session to disconnect
            # from the parent's controlling terminal
            os.setsid()
    
            # set the controlling terminal to the pty
            # by opening it (and closing it again since
            # it's already open as child_stdout)
            fd = os.open(tty, os.O_RDWR);
            os.close(fd)

        # init stdin/out/err
        os.dup2(child_stdin,  0)
        os.dup2(child_stdout, 1)
        if child_stderr >= 0:
            os.dup2(child_stderr, 2)
    
        # finally, execute the child
        if env:
            os.execv(command, args, env)
        else:
            os.execv(command, args)

    # parent process
    else:

        # close all of the child's fds
        os.close(child_stdin)
        if child_stdout != child_stdin:
            os.close(child_stdout)
        if child_stderr >= 0 and child_stderr != child_stdin and child_stderr != child_stdout:
            os.close(child_stderr)

        return pid, _pty_file(parent_stdout), os.fdopen(parent_stdin, 'w')


### Tests ###

if __name__ == '__main__':

    import sys
    pid, recv, send = popeni('/usr/sbin/kadmin.local', ['kadmin'])

    send.write("listprincs\n")
    send.flush()

    print recv.readlines()
