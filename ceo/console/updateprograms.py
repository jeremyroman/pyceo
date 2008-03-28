import ldap, sys, termios
from ceo import members, uwldap, ldapi

class UpdatePrograms:
  help = '''
updateprograms

Interactively updates the program field for an account by querying uwdir.
'''
  def main(self, args):
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
      if oldprog == newprog or newprog == '':
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
      #if newprog != '':
      #  members.set_program(uid, newprog)
      members.ld.modify_s(dn, mlist)
