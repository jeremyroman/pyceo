from ceo import members, terms
import re

class MathSocList:
  help = '''
mathsoclist [term]

Displays a list of members for a term that are likely to be paying MathSoc
members; defaults to the current term if term is not given.
'''

  regex = ".*(mat/|vpa/se|computer science|math).*"
  noinc = [ "dtbartle", "dlgawley", "cpdohert", "mbiggs", "tmyklebu" ]

  def main(self, args):
    regex = re.compile(self.regex)
    if len(args) == 1:
        mlist = members.list_term(args[0])
    else:
        mlist = members.list_term(terms.current())
    dns = mlist.keys()
    dns.sort()
    for dn in dns:
      member = mlist[dn]
      if member['uid'][0] in self.noinc:
        continue
      program = member.get('program', [''])[0]
      if regex.match(program.lower()) != None:
        print '%s %s %s' % (
          member['uid'][0].ljust(12),
          member['cn'][0].ljust(30),
          member.get('program', [''])[0]
        )
