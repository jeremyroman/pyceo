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
from csc.common.excep import InvalidArgument

# color of the ceo border
BORDER_COLOR = curses.COLOR_RED


def read_uid(wnd):
    """Read a username."""

    prompt = 'Username:'
    return inputbox(wnd, prompt, 36)

def read_member(wnd):
    """Looks up a member."""

    # connect the members module to its backend if necessary
    if not members.connected(): members.connect()

    uid = read_uid(wnd)
    if not uid or uid.lower() == 'exit':
        return

    member = members.get(uid)
    if not member:
        msgbox(wnd, "Invalid username: %s" % uid)
        return

    # display user
    display_member_details(wnd, member)

    return member


def action_library(wnd):
    """Display a link to the library."""
    msgbox(wnd, "Please visit library.csclub.uwaterloo.ca")

def action_new_member(wnd):
    """Interactively add a new member."""

    userid, studentid, program = '', None, ''

    msgbox(wnd, "Membership is $2.00 CDN. Please ensure\n"
                "the money is desposited in the safe\n"
                "before continuing.")

    # read the name
    prompt = "New member's full name: "
    realname = inputbox(wnd, prompt, 30)

    # abort if no name is entered
    if not realname or realname.lower() == 'exit':
        return False

    # read the student id
    prompt = "New member's student ID:"
    while studentid is None or (re.search("[^0-9]", studentid) and not studentid.lower() == 'exit'):
        studentid = inputbox(wnd, prompt, 30)

    # abort if exit is entered
    if studentid.lower() == 'exit':
        return False

    if studentid == '':
        studentid = None

    # read the program of study
    prompt = "New member's program of study:"
    program = inputbox(wnd, prompt, 30)

    # abort if exit is entered
    if program is None or program.lower() == 'exit':
        return False

    # read user id
    prompt = "New member's UWdir username:"
    while userid == '':
        userid = inputbox(wnd, prompt, 30)

    # user abort
    if userid is None or userid.lower() == 'exit':
        return False

    # connect the members module to its backend if necessary
    if not members.connected(): members.connect()

    # attempt to create the member
    try:
        members.new(userid, realname, studentid, program)

        msgbox(wnd, "Success! Your username is %s.  You are now registered\n"
                    % userid + "for the " + terms.current() + " term.")

    except members.InvalidStudentID:
        msgbox(wnd, "Invalid student ID: %s" % studentid)
        return False
    except members.DuplicateStudentID:
        msgbox(wnd, "A member with this student ID exists.")
        return False
    except members.InvalidRealName:
        msgbox(wnd, 'Invalid real name: "%s"' % realname)
        return False
    except InvalidArgument, e:
        if e.argname == 'uid' and e.explanation == 'duplicate uid':
            msgbox(wnd, 'A member with this user ID exists.')
            return False
        else:
            raise


def action_term_register(wnd):
    """Interactively register a member for a term."""

    term = ''

    member = read_member(wnd)
    if not member:
        return False
    uid = member['uid'][0]

    # verify member
    prompt = "Is this the correct member?"
    answer = None
    while answer != "yes" and answer != "y" and answer != "n" and answer != "no" and answer != "exit":
        answer = inputbox(wnd, prompt, 28) 

    # user abort
    if answer == "exit":
        return False

    # read the term
    prompt = "Which term to register for ([wsf]20nn):"
    while not re.match('^[wsf][0-9]{4}$', term) and not term == 'exit':
        term = inputbox(wnd, prompt, 41) 

    # abort when exit is entered
    if term.lower() == 'exit':
        return False

    # already registered?
    if members.registered(uid, term):
        msgbox(wnd, "You are already registered for term " + term)
        return False

    try:

        # attempt to register
        members.register(uid, term)
        
        # display success message
        msgbox(wnd, "You are now registered for term " + term)

    except members.InvalidTerm:
        msgbox(wnd, "Term is not valid: %s" % term)

    return False


def action_term_register_multiple(wnd):
    """Interactively register a member for multiple terms."""

    base, num = '', None

    member = read_member(wnd)
    if not member:
        return False
    uid = member['uid'][0]

    # verify member
    prompt = "Is this the correct member?"
    answer = None
    while answer != "yes" and answer != "y" and answer != "n" and answer != "no" and answer != "exit":
        answer = inputbox(wnd, prompt, 28) 

    # user abort
    if answer == "exit":
        return False

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
        if members.registered(uid, term):
            msgbox(wnd, "You are already registered for term " + term)
            return False

    try:

        # attempt to register all terms
        members.register(uid, term_list)
        
        # display success message [sic]
        msgbox(wnd, "Your are now registered for terms: " + ", ".join(term_list))

    except members.InvalidTerm:
        msgbox(wnd, "Invalid term entered.")

    return False


def input_password(wnd):

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

    return password


def action_create_account(wnd):
    """Interactively create an account for a member."""
    
    member = read_member(wnd)
    if not member:
        return False

    # member already has an account?
    if not accounts.connected(): accounts.connect()
    if 'posixAccount' in member['objectClass']:
        msgbox(wnd, "Account already exists.")
        return False

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

    msgbox(wnd, "Ensure the member has signed the machine\n"
                "usage policy. Accounts of users who have\n"
                "not signed will be suspended if discovered.")

    # read password
    password = input_password(wnd)

    # create the UNIX account
    try:
        if not accounts.connected(): accounts.connect()
        accounts.create_member(member['uid'][0], password, member['cn'][0])
    except accounts.NameConflict, e:
        msgbox(wnd, str(e))
        return False
    except accounts.NoAvailableIDs, e:
        msgbox(wnd, str(e))
        return False
    except accounts.InvalidArgument, e:
        msgbox(wnd, str(e))
        return False
    except accounts.LDAPException, e:
        msgbox(wnd, "Error creating LDAP entry - Contact the Systems Administrator: %s" % e)
        return False
    except accounts.KrbException, e:
        msgbox(wnd, "Error creating Kerberos principal - Contact the Systems Administrator: %s" % e)
        return False

    # success
    msgbox(wnd, "Please run 'addhomedir " + member['uid'][0] + "'.")
    msgbox(wnd, "Success! Your account has been added")

    return False


def display_member_details(wnd, member):
    """Display member attributes in a message box."""

    # clone and sort term_list
    if 'term' in member:
        term_list = list(member['term'])
    else:
        term_list = []
    term_list.sort( terms.compare )

    # labels for data
    id_label, studentid_label, name_label = "ID:", "StudentID:", "Name:"
    program_label, terms_label = "Program:", "Terms:"

    if 'program' in member:
        program = member['program'][0]
    else:
        program = None

    if 'studentid' in member:
        studentid = member['studentid'][0]
    else:
        studentid = None

    # format it all into a massive string
    message =  "%8s %-20s %10s %-10s\n" % (name_label, member['cn'][0], id_label, member['uid'][0]) + \
               "%8s %-20s %10s %-10s\n" % (program_label, program, studentid_label, studentid)

    message += "%s %s" % (terms_label, " ".join(term_list))

    # display the string in a message box
    msgbox(wnd, message)
    

def action_display_member(wnd):
    """Interactively display a member."""
    
    if not members.connected(): members.connect()
    member = read_member(wnd)
    return False


def page(text):
    """Send a text buffer to an external pager for display."""
    
    try:
        pager = '/usr/bin/less'
        pipe = os.popen(pager, 'w')
        pipe.write(text)
        pipe.close() 
    except IOError:
        # broken pipe (user didn't read the whole list)
        pass
    

def format_members(member_list):
    """Format a member list into a string."""

    # clone and sort member_list
    member_list = list(member_list)
    member_list.sort( lambda x, y: cmp(x['uid'], y['uid']) )

    buf = ''
    
    for member in member_list:
        if 'uid' in member:
            uid = member['uid'][0]
        else:
            uid = None
        if 'program' in member:
            program = member['program'][0]
        else:
            program = None
        if 'studentid' in member:
            studentid = member['studentid'][0]
        else:
            studentid = None
        attrs = ( uid, member['cn'][0],
                studentid, program )
        buf += "%10s %30s %10s\n%41s\n\n" % attrs

    return buf


def action_list_term(wnd):
    """Interactively list members registered in a term."""

    term = None

    # read the term
    prompt = "Which term to list members for ([fws]20nn): "
    while term is None or (not term == '' and not re.match('^[wsf][0-9]{4}$', term) and not term == 'exit'):
        term = inputbox(wnd, prompt, 41) 

    # abort when exit is entered
    if not term or term.lower() == 'exit':
        return False

    # connect the members module to its backends if necessary
    if not members.connected(): members.connect()
    
    # retrieve a list of members for term
    member_list = members.list_term(term)

    # format the data into a mess of text
    buf = format_members(member_list.values())

    # display the mass of text with a pager
    page( buf )

    return False


def action_list_name(wnd):
    """Interactively search for members by name."""
    
    name = None

    # read the name
    prompt = "Enter the member's name: "
    name = inputbox(wnd, prompt, 41) 

    # abort when exit is entered
    if not name or name.lower() == 'exit':
        return False

    # connect the members module to its backends if necessary
    if not members.connected(): members.connect()
    
    # retrieve a list of members with similar names
    member_list = members.list_name(name)

    # format the data into a mess of text
    buf = format_members(member_list.values())

    # display the mass of text with a pager
    page( buf )

    return False


def action_list_studentid(wnd):
    """Interactively search for members by student id."""

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
    member_list = members.get_studentid(studentid)

    # format the data into a mess of text
    buf = format_members(member_list.values())

    # display the mass of text with a pager
    page( buf )

    return False


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
    ( "Library functions", action_library ),
    ( "Exit", exit_callback ),
]


def acquire_ceo_wnd(screen=None):
    """Create the top level ceo window."""
    
    # hack to get a reference to the entire screen
    # even when the caller doesn't (shouldn't) have one
    if screen is None:
        screen = globals()['screen']
    else:
        globals()['screen'] = screen

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

    try:
        # display the top level menu
        menu(ceo_wnd, menu_y, menu_x, menu_width, top_menu, acquire_ceo_wnd)
    finally:
        members.disconnect()
        accounts.disconnect()


def run():
    """Main function for legacy UI."""

    # workaround for xterm-color (bad terminfo? - curs_set(0) fails)
    if "TERM" in os.environ and os.environ['TERM'] == "xterm-color":
        os.environ['TERM'] = "xterm"

    # wrap the entire program using curses.wrapper
    # so that the terminal is restored to a sane state
    # when the program exits
    try:
        curses.wrapper(ceo_main_curses)
    except KeyboardInterrupt:
        pass
    except curses.error:
        print "Is your screen too small?"
        raise
    except:
        reset()
        raise

    # clean up screen before exit
    reset()

if __name__ == '__main__':
    run()

