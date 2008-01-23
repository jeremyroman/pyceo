import sys, ldap, termios
from getopt import getopt
from ceo import members, terms, uwldap
import ceo.ldapi as ldapi

shortopts = [
]

longopts = [
]

def start():
  (opts, args) = getopt(sys.argv[1:], shortopts, longopts)
  if len(args) >= 1:
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
  uwl = ldap.initialize(uwldap.uri())
  fd = sys.stdin.fileno()
  for (dn, member) in mlist:
    uid = member['uid'][0]
    user = uwl.search_s(uwldap.base(), ldap.SCOPE_SUBTREE,
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

def expiredaccounts(args):
  send_email = False
  if len(args) == 1 and args[0] == '--email':
    sys.stderr.write("If you want to send an account expiration notice to " \
      "these users then type 'Yes, do this' and hit enter\n")
    if raw_input() == 'Yes, do this':
      send_email = True
  uwl = ldap.initialize(uwldap.uri())
  mlist = members.expired_accounts()
  for member in mlist.values():
    uid = member['uid'][0]
    name = member['cn'][0]
    email = None
    if send_email:
      members.send_account_expired_email(name, uid)
      user = uwl.search_s(uwldap.base(), ldap.SCOPE_SUBTREE,
        '(uid=%s)' % ldapi.escape(uid))
      if len(user) > 0  and 'mailLocalAddress' in user[0][1]:
        email = user[0][1]['mailLocalAddress'][0]
        members.send_account_expired_email(name, email)
    print '%s %s' % (uid.ljust(12), name.ljust(30))

# list of commands
commands = {
  'memberlist' : memberlist,
  'updateprogram' : updateprogram,
  'expiredaccounts' : expiredaccounts,
}
