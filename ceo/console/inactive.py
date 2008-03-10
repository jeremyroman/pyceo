from ceo import members, terms

def max_term(term1, term2):
    if terms.compare(term1, term2) > 0:
        return term1
    else:
        return term2

class Inactive:
  def main(self, args):
    if len(args) != 1:
        print "Usage: ceo inactive delta-terms"
        return
    delta = int(args[0])
    mlist = members.list_all()
    for member in mlist.values():
        term = "f0000"
        term = reduce(max_term, member.get("term", []), term)
        term = reduce(max_term, member.get("nonMemberTerm", []), term)
        if terms.delta(term, terms.current()) > delta:
            print "%s %s" % (member['uid'][0].ljust(12), term)
