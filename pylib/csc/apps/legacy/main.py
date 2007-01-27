# $Id: main.py 44 2006-12-31 07:09:27Z mspang $
"""
CEO-like Frontend

This frontend aims to be compatible in both look and function with the
curses UI of CEO.

Some small improvements have been made, such as not echoing passwords and
aborting when nothing is typed into the first input box during an operation.

This frontend is poorly documented, deprecated, and undoubtedly full of bugs.
"""
import curses.ascii, re, os
from helpers import menu, inputbox, msgbox, reset
from csc.adm import accounts, members, terms

# color of the ceo border
BORDER_COLOR = curses.COLOR_RED


def action_new_member(wnd):
    """Interactively add a new member."""

    username, studentid, program = '', None, ''

    # read the name
    prompt = "      Name: "
    realname = inputbox(wnd, prompt, 18)

    # abort if no username is entered
    if not realname or realname.lower() == 'exit':
        return False

    # read the student id
    prompt = "Student id:"
    while studentid == None or (re.search("[^0-9]", studentid) and not studentid.lower() == 'exit'):
        studentid = inputbox(wnd, prompt, 18)

    # abort if exit is entered
    if studentid.lower() == 'exit':
        return False

    if studentid == '':
        studentid = None

    # read the program of study
    prompt = "   Program:"
    program = inputbox(wnd, prompt, 18)

    # abort if exit is entered
    if program == None or program.lower() == 'exit':
        return False

    # connect the members module to its backend if necessary
    if not members.connected(): members.connect()

    # attempt to create the member
    try:
        memberid = members.new(realname, studentid, program)

        msgbox(wnd, "Success! Your memberid is %s.  You are now registered\n"
                    % memberid + "for the " + terms.current() + " term.");

    except members.InvalidStudentID:
        msgbox(wnd, "Invalid student ID.")
        return False
    except members.DuplicateStudentID:
        msgbox(wnd, "A member with this student ID exists.")
        return False


def action_term_register(wnd):
    """Interactively register a member for a term."""

    memberid, term = '', ''

    # read the member id
    prompt = 'Enter memberid ("exit" to cancel):'
    memberuserid = inputbox(wnd, prompt, 36)

    if not memberuserid or memberuserid.lower() == 'exit':
        return False

    member = get_member_memberid_userid(wnd, memberuserid)
    if not member: return False

    memberid = member['memberid']
    term_list = members.terms_list(memberid)
    
    # display user
    display_member_details(wnd, member, term_list)

    # read the term
    prompt = "Which term to register for ([fws]20nn):"
    while not re.match('^[wsf][0-9]{4}$', term) and not term == 'exit':
        term = inputbox(wnd, prompt, 41) 

    # abort when exit is entered
    if term.lower() == 'exit':
        return False

    # already registered?
    if members.registered(memberid, term):
        msgbox(wnd, "You are already registered for term " + term)
        return False

    try:

        # attempt to register
        members.register(memberid, term)
        
        # display success message [sic]
        msgbox(wnd, "Your are now registered for term " + term)

    except members.InvalidTerm:
        msgbox(wnd, "Term is not valid: %s" % term)

    return False


def action_term_register_multiple(wnd):
    """Interactively register a member for multiple terms."""

    memberid, base, num = '', '', None

    # read the member id
    prompt = 'Enter memberid ("exit" to cancel):'
    memberuserid = inputbox(wnd, prompt, 36)

    if not memberuserid or memberuserid.lower() == 'exit':
        return False

    member = get_member_memberid_userid(wnd, memberuserid)
    if not member: return False

    memberid = member['memberid']
    term_list = members.terms_list(memberid)
    
    # display user
    display_member_details(wnd, member, term_list)

    # read the base
    prompt = "Which term to start registering ([fws]20nn):"
    while not re.match('^[wsf][0-9]{4}$', base) and not base == 'exit':
        base = inputbox(wnd, prompt, 41) 

    # abort when exit is entered
    if base.lower() == 'exit':
        return False

    # read number of terms
    prompt = 'How many terms?'
    while not num or not re.match('^[0-9]*$', num):
        num = inputbox(wnd, prompt, 36)
    num = int(num)

    # any terms in the range?
    if num < 1:
        msgbox(wnd, "No terms to register.")
        return False

    # compile a list to register
    term_list = terms.interval(base, num)

    # already registered?
    for term in term_list:
        if members.registered(memberid, term):
            msgbox(wnd, "You are already registered for term " + term)
            return False

    try:

        # attempt to register all terms
        members.register(memberid, term_list)
        
        # display success message [sic]
        msgbox(wnd, "Your are now registered for terms: " + ", ".join(term_list))

    except members.InvalidTerm:
        msgbox(wnd, "Term is not valid: %s" % term)

    return False


def action_create_account(wnd):
    """Interactively create an account for a member."""
    
    memberid, userid = '', ''

    # read the member id
    prompt = 'Enter member ID (exit to cancel):'
    memberid = inputbox(wnd, prompt, 35)

    if not memberid or memberid.lower() == 'exit':
        return False

    member = get_member_memberid_userid(wnd, memberid)
    if not member: return False

    memberid = member['memberid']
    term_list = members.terms_list(memberid)
    
    # display the member
    display_member_details(wnd, member, term_list)
    
    # verify member
    prompt = "Is this the correct member?"
    answer = None
    while answer != "yes" and answer != "y" and answer != "n" and answer != "no" and answer != "exit":
        answer = inputbox(wnd, prompt, 28) 

    # user abort
    if answer == "exit":
        return False

    # incorrect member; abort
    if answer == "no" or answer == "n":
        msgbox(wnd, "I suggest searching for the member by userid or name from the main menu.")
        return False

    # read user id
    prompt = "Userid:"
    while userid == '':
        userid = inputbox(wnd, prompt, 18) 

    # user abort
    if userid == None or userid.lower() == 'exit':
        return False

    # member already has an account?
    #if member['userid'] != None:
    #    msgbox(wnd, "Member " + str(memberid) + " already has an account: " + member['userid'] + "\n"
    #                "Contact the sysadmin if there are still problems." )
    #    return False

    # password input loop
    password = "password"
    check = "check"
    while password != check:
    
        # read password
        prompt = "User password:"
        password = None
        while not password:
            password = inputbox(wnd, prompt, 18, False) 

        # read another password
        prompt = "Enter the password again:"
        check = None
        while not check:
            check = inputbox(wnd, prompt, 27, False) 


    # create the UNIX account
    result = accounts.create_account(userid, password, member['name'], memberid)

    if result == accounts.LDAP_EXISTS:
        msgbox(wnd, "Error: Could not do stuff , Already exists.")
        return False
    elif result == accounts.KRB_EXISTS:
        msgbox(wnd, "This account already exists in Kerberos, but not in LDAP. Please contact the Systems Administrator.")
        return False
    elif result == accounts.LDAP_NO_IDS:
        msgbox(wnd, "There are no available UNIX user ids. This is a fatal error. Contact the Systems Administrator.")
        return False
    elif result == accounts.BAD_REALNAME:
        msgbox(wnd, "Invalid real name: %s. Contact the Systems Administrator." % member['name'])
        return False
    elif result == accounts.BAD_USERNAME:
        msgbox(wnd, "Invalid username: %s. Enter a valid username." % userid)
        return False
    elif result != accounts.SUCCESS:
        raise Exception("Unexpected return status of accounts.create_account(): %s" % result)
        
    # now update the CEO database with the username
    members.update( {'memberid':memberid, 'userid': userid} )

    # success
    msgbox(wnd, "Please run 'addhomedir " + userid + "'.")
    msgbox(wnd, "Success! Your account has been added")


def display_member_details(wnd, member, term_list):
    """Display member attributes in a message box."""

    # clone and sort term_list
    term_list = list(term_list)
    term_list.sort( terms.compare )

    # labels for data
    id_label, studentid_label, name_label = "ID:", "StudentID:", "Name:"
    program_label, userid_label, terms_label = "Program:", "User ID:", "Terms:"

    # format it all into a massive string
    message =  "%8s %-20s %10s %-10s (user)\n" % (name_label, member['name'], id_label, member['memberid']) + \
               "%8s %-20s %10s %-10s\n" % (program_label, member['program'], studentid_label, member['studentid'])

    if member['userid']:
        message += "%8s %s\n" % (userid_label, member['userid'])
    else:
        message += 'No user ID.\n'

    message += "%s %s" % (terms_label, " ".join(term_list))

    # display the string in a message box
    msgbox(wnd, message)


def get_member_memberid_userid(wnd, memberuserid):
    """Retrieve member attributes by member of user id."""

    # connect the members module to its backends
    if not members.connected(): members.connect()

    # retrieve member data

    if re.match('^[0-9]*$', memberuserid):

        # numeric memberid, look it up
        memberid = int(memberuserid)
        member = members.get( memberid )
        if not member:
            msgbox(wnd, '%s is an invalid memberid' % memberuserid)

    else:

        # non-numeric memberid: try userids
        member = members.get_userid( memberuserid )
        if not member:
            msgbox(wnd, "%s is an invalid account userid" % memberuserid)
            
    return member
    

def action_display_member(wnd):
    """Interactively display a member."""
    
    # read the member id
    prompt = 'Memberid: '
    memberid = inputbox(wnd, prompt, 36)

    if not memberid or memberid.lower() == 'exit':
        return False

    member = get_member_memberid_userid(wnd, memberid)
    if not member: return
    term_list = members.terms_list( member['memberid'] )

    # display the details in a window
    display_member_details(wnd, member, term_list)


def page(text):
    
    try:
        pipe = os.popen('/usr/bin/less', 'w')
        pipe.write(text)
        pipe.close() 
    except IOError:
        # broken pipe (user didn't read the whole list)
        pass
    

def format_members(member_list):
    """Format a member list into a string."""

    # clone and sort member_list
    member_list = list(member_list)
    member_list.sort( lambda x, y: x['memberid']-y['memberid'] )

    buf = ''
    
    for member in member_list:
        attrs = ( member['memberid'], member['name'], member['studentid'],
                member['type'], member['program'], member['userid'] )
        buf += "%4d %50s %10s %10s \n%55s %10s\n\n" % attrs

    return buf


def action_list_term(wnd):
    """Interactively list members registered in a term."""

    term = None

    # read the term
    prompt = "Which term to list members for ([fws]20nn): "
    while term == None or (not term == '' and not re.match('^[wsf][0-9]{4}$', term) and not term == 'exit'):
        term = inputbox(wnd, prompt, 41) 

    # abort when exit is entered
    if not term or term.lower() == 'exit':
        return False

    # connect the members module to its backends if necessary
    if not members.connected(): members.connect()
    
    # retrieve a list of members for term
    member_list = members.list_term(term)

    # format the data into a mess of text
    buf = format_members(member_list)

    # display the mass of text with a pager
    page( buf )


def action_list_name(wnd):
    
    name = None

    # read the name
    prompt = "Enter the member's name: "
    name = inputbox(wnd, prompt, 41) 

    # abort when exit is entered
    if not name or name.lower() == 'exit':
        return False

    # connect the members module to its backends if necessary
    if not members.connected(): members.connect()
    
    # retrieve a list of members for term
    member_list = members.list_name(name)

    # format the data into a mess of text
    buf = format_members(member_list)

    # display the mass of text with a pager
    page( buf )


def action_list_studentid(wnd):

    studentid = None

    # read the studentid
    prompt = "Enter the member's student id: "
    studentid = inputbox(wnd, prompt, 41) 

    # abort when exit is entered
    if not studentid or studentid.lower() == 'exit':
        return False

    # connect the members module to its backends if necessary
    if not members.connected(): members.connect()
    
    # retrieve a list of members for term
    member = members.get_studentid(studentid)
    if member != None:
        member_list = [ members.get_studentid(studentid) ]
    else:
        member_list = []

    # format the data into a mess of text
    buf = format_members(member_list)

    # display the mass of text with a pager
    page( buf )


def null_callback(wnd):
    """Callback for unimplemented menu options."""
    return False


def exit_callback(wnd):
    """Callback for the exit option."""
    return True


# the top level ceo menu
top_menu = [
    ( "New member", action_new_member ),
    ( "Register for a term", action_term_register ),
    ( "Register for multiple terms", action_term_register_multiple ),
    ( "Display a member", action_display_member ),
    ( "List members registered in a term", action_list_term ),
    ( "Search for a member by name", action_list_name ),
    ( "Search for a member by student id", action_list_studentid ),
    ( "Create an account", action_create_account ),
    ( "Re Create an account", null_callback ),
    ( "Library functions", null_callback ),
    ( "Exit", exit_callback ),
]


def acquire_ceo_wnd(screen=None):
    """Create the top level ceo window."""
    
    # hack to get a reference to the entire screen
    # even when the caller doesn't (shouldn't) have one
    global _screen
    if screen == None:
        screen = _screen
    else:
        _screen = screen

    # if the screen changes size, a mess may be left
    screen.erase()

    # for some reason, the legacy ceo system
    # excluded the top line from its window
    height, width = screen.getmaxyx()
    ceo_wnd = screen.subwin(height-1, width, 1, 0)

    # draw the border around the ceo window
    curses.init_pair(1, BORDER_COLOR, -1)
    color_attr = curses.color_pair(1) | curses.A_BOLD
    ceo_wnd.attron(color_attr)
    ceo_wnd.border()
    ceo_wnd.attroff(color_attr)

    # return window and dimensions of inner area
    return ceo_wnd, 1, 1, height-2, width-2


def ceo_main_curses(screen):
    """Wrapped main for curses."""
    
    curses.use_default_colors()

    # workaround for SSH sessions on virtual consoles (reset terminal)
    reset()

    # create ceo window
    ceo_wnd, menu_y, menu_x, menu_height, menu_width = acquire_ceo_wnd(screen)

    # display the top level menu
    menu(ceo_wnd, menu_y, menu_x, menu_width, top_menu, acquire_ceo_wnd)


def run():
    """Main function for legacy UI."""

    # wrap the entire program using curses.wrapper
    # so that the terminal is restored to a sane state
    # when the program exits
    try:
        curses.wrapper(ceo_main_curses)
    except KeyboardInterrupt:
        pass
    except curses.error:
        print "Your screen is too small!"
        raise
    except:
        reset()
        raise

    # clean up screen before exit
    reset()

if __name__ == '__main__':
    run()

