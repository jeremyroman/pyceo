import os
import subprocess

class RemoteException(Exception):
    """Exception class for bad argument values."""
    def __init__(self, status, stdout, stderr):
        self.status, self.stdout, self.stderr = status, stdout, stderr
    def __str__(self):
        return 'Error executing ceoc (%d)\n\n%s' % (self.status, self.stderr)

def run_remote(op, data):
    ceoc = '%s/ceoc' % os.environ.get('CEO_LIB_DIR', '/usr/lib/ceod')
    addmember = subprocess.Popen([ceoc, op], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = addmember.communicate(data)
    status = addmember.wait()
    if status:
        raise RemoteException(status, out, err)
    return out
