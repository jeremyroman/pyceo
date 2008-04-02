import sys, ldap, termios
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
help_opts = [ '--help', '-h' ]

def start():
  args = sys.argv[1:]
  if args[0] in help_opts:
    help()
  elif args[0] in commands:
    command = commands[args[0]]
    if len(args) >= 2 and args[1] in help_opts:
      print command.help
    else:
      command.main(args[1:])
  else:
    print "Invalid command '%s'" % args[0]

def help():
  args = sys.argv[2:]
  if len(args) == 1:
    if args[0] in commands:
      print commands[args[0]].help
    else:
      print 'Unknown command %s.' % args[0]
  else:
    print ''
    print 'To run the ceo GUI, type \'ceo\''
    print ''
    print 'To run a ceo console command, type \'ceo command\''
    print ''
    print 'Available console commands:'
    for c in commands:
      print '  %s' % c
    print ''
    print 'Run \'ceo command --help\' for help on a specific command.'
    print ''
