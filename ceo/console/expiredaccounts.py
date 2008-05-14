import sys, ldap
from ceo import members, uwldap

class ExpiredAccounts:
  help = '''
expiredaccounts [--email]

Displays a list of expired accounts. If --email is specified, expired account
owners will be emailed. The email will go to the email listed in uwdir.
'''

  def main(self, args):
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
