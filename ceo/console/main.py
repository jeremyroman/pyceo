import sys
from getopt import getopt
from ceo import members, terms

shortopts = [
]

longopts = [
]

def start():
  (opts, args) = getopt(sys.argv[1:], shortopts, longopts)
  if len(args) == 1:
    if args[0] == 'memberlist':
      mlist = members.list_term(terms.current()).values()
      for member in mlist:
        print '%s %s %s' % (
          member['uid'][0].ljust(12),
          member['cn'][0].ljust(30),
          member.get('program', [''])[0]
        )
    else:
      print "Invalid argument '%s'" % args[0]

def help():
  print 'ceo memberlist'
