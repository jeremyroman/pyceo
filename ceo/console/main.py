import sys, ldap, termios
from getopt import getopt
from ceo import members, terms, uwldap, ldapi

from ceo.console.memberlist import MemberList
from ceo.console.updateprograms import UpdatePrograms
from ceo.console.expiredaccounts import ExpiredAccounts
from ceo.console.inactive import Inactive

commands = {
  'memberlist' : MemberList(),
  'updateprograms' : UpdatePrograms(),
  'expiredaccounts' : ExpiredAccounts(),
  'inactive': Inactive(),
}

shortopts = [
]

longopts = [
]

def start():
  (opts, args) = getopt(sys.argv[1:], shortopts, longopts)
  if len(args) >= 1:
    if args[0] in commands:
      commands[args[0]].main(args[1:])
    else:
      print "Invalid command '%s'" % args[0]

def help():
  print 'Available commands:'
  for c in commands:
    print '  %s' % c
