from ceo import members, terms

class MemberList:
  help = '''
memberlist [term]

Displays a list of members for a term; defaults to the current term if term
is not given.
'''
  def main(self, args):
    mlist = {}
    if len(args) == 1:
        mlist = members.list_term(args[0])
    else:
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
