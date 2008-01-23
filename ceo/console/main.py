import sys, ldap, termios
from getopt import getopt
from ceo import members, terms
import ceo.ldapi as ldapi

shortopts = [
]

longopts = [
]

def start():
  (opts, args) = getopt(sys.argv[1:], shortopts, longopts)
  if len(args) == 1:
    if args[0] in commands:
      commands[args[0]](args[1:])
    else:
      print "Invalid command '%s'" % args[0]

def help():
  print 'Available commands:'
  for c in commands:
    print '  %s' % c

def memberlist(args):
  mlist = members.list_term(terms.current())
  dns = mlist.keys()
  dns.sort()
  for dn in dns:
    member = mlist[dn]
    print '%s %s %s' % (
      member['uid'][0].ljust(12),
      member['cn'][0].ljust(30),
      member.get('program', [''])[0]
    )

def updateprogram(args):
  mlist = members.list_all().items()
  uwldap = ldap.initialize(uwldap_uri())
  fd = sys.stdin.fileno()
  for (dn, member) in mlist:
    uid = member['uid'][0]
    user = uwldap.search_s(uwldap_base(), ldap.SCOPE_SUBTREE,
      '(uid=%s)' % ldapi.escape(uid))
    if len(user) == 0:
      continue
    user = user[0][1]
    oldprog = member.get('program', [''])[0]
    newprog = user.get('ou', [''])[0]
    if oldprog == newprog:
      continue
    sys.stdout.write("%s: '%s' => '%s'? (y/n) " % (uid, oldprog, newprog))
    new = old = termios.tcgetattr(fd)
    new[3] = new[3] & ~termios.ICANON
    try:
      termios.tcsetattr(fd, termios.TCSANOW, new)
      try:
        if sys.stdin.read(1) != 'y':
          continue
      except KeyboardInterrupt:
        return ''
    finally:
      print ''
      termios.tcsetattr(fd, termios.TCSANOW, old)
    old = new = {}
    if oldprog != '':
      old = {'program': [oldprog]}
    if newprog != '':
      new = {'program': [newprog]}
    mlist = ldapi.make_modlist(old, new)
    # TODO: don't use members.ld directly
    members.ld.modify_s(dn, mlist)


# list of commands
commands = {
  'memberlist' : memberlist,
  'updateprogram' : updateprogram,
}
