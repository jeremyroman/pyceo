from ceo import members, terms

class MemberList:
  def main(self, args):
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
