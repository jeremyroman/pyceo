# $Id: helpers.py 35 2006-12-28 05:14:05Z mspang $
"""
Helpers for legacy User Interface

This module contains numerous functions that are designed to immitate
the look and behavior of the previous CEO. Included is code for various
curses-based UI widgets that were provided by Perl 5's Curses and
Curses::Widgets libraries.

Though attempts have been made to keep the UI bug-compatible with
the previous system, some compromises have been made. For example,
the input and textboxes draw 'OK' and 'Cancel' buttons where the old
CEO had them, but they are fake. That is, the buttons in the old
CEO were selectable but non-operational, but in the new CEO they are
not even selectable.
"""
import curses.ascii

# key constants not defined in CURSES
KEY_RETURN = ord('\n')
KEY_ESCAPE = 27
KEY_EOT = 4


def center(parent_dim, child_dim):
    """Helper for centering a length in a larget length."""
    return (parent_dim-child_dim)/2


def read_input(wnd, offy, offx, width, maxlen, echo=True):
    """
    Read user input within a confined region of a window.

    Basic line-editing is supported:
        LEFT, RIGHT, HOME, and END move around.
        BACKSPACE and DEL remove characters.
        INSERT switches between insert and overwrite mode.
        ESC and C-d abort input.
        RETURN completes input.
    
    Parameters:
        wnd    - parent window for region
        offy   - the vertical offset for the beginning of the input region
        offx   - the horizontal offset for the beginning of the input region
        width  - the width of the region
        maxlen - greatest number of characters to read (0 for no limit)
        echo   - boolean: whether to display typed characters
    
    Returns: the string, or None when the user aborts.
    """

    # turn on cursor
    try:
        curses.curs_set(1)
    except:
        pass

    # set keypad mode to allow UP, DOWN, etc
    wnd.keypad(1)

    # the input string
    input = ""

    # offset of cursor in input
    # i.e. the next operation is applied at input[inputoff]
    inputoff = 0

    # display offset (for scrolling)
    # i.e. the first character in the region is input[displayoff]
    displayoff = 0

    # insert mode (True) or overwrite mode (False)
    insert = True

    while True:

        # echo mode, display the string
        if echo:
            # discard characters before displayoff, 
            # as the window may be scrolled to the right
            substring = input[displayoff:]
    
            # pad the string with zeroes to overwrite stale characters
            substring = substring + " " * (width - len(substring))
    
            # display the substring
            wnd.addnstr(offy, offx, substring, width)
    
            # await input
            key = wnd.getch(offy, offx + inputoff - displayoff)

        # not echo mode, don't display the string
        else:
            # await input at arbitrary location
            key = wnd.getch(offy, offx)

        # enter returns input
        if key == KEY_RETURN:
            return input

        # escape aborts input
        elif key == KEY_ESCAPE:
            return None

        # EOT (C-d) aborts if there is no input
        elif key == KEY_EOT:
            if len(input) == 0:
                return None

        # backspace removes the previous character
        elif key == curses.KEY_BACKSPACE:
            if inputoff > 0:

                # remove the character immediately before the input offset
                input = input[0:inputoff-1] + input[inputoff:]
                inputoff -= 1

                # move either the cursor or entire line of text left
                if displayoff > 0:
                    displayoff -= 1

        # delete removes the current character
        elif key == curses.KEY_DC:
            if inputoff < len(input):
                
                # remove the character at the input offset
                input = input[0:inputoff] + input[inputoff+1:]

        # left moves the cursor one character left
        elif key == curses.KEY_LEFT:
            if inputoff > 0:

                # move the cursor to the left
                inputoff -= 1

                # scroll left if necessary
                if inputoff < displayoff:
                    displayoff -= 1

        # right moves the cursor one character right
        elif key == curses.KEY_RIGHT:
            if inputoff < len(input):
                
                # move the cursor to the right
                inputoff += 1

                # scroll right if necessary
                if displayoff - inputoff == width:
                    displayoff += 1

        # home moves the cursor to the first character
        elif key == curses.KEY_HOME:
            inputoff = 0
            displayoff = 0

        # end moves the cursor past the last character
        elif key == curses.KEY_END:
            inputoff = len(input)
            displayoff = len(input) - width + 1

        # insert toggles insert/overwrite mode
        elif key == curses.KEY_IC:
            insert = not insert

        # other (printable) characters are added to the input string
        elif curses.ascii.isprint(key):
            if len(input) < maxlen or maxlen == 0:

                # insert mode: insert before current offset
                if insert:
                    input = input[0:inputoff] + chr(key) + input[inputoff:]
    
                # overwrite mode: replace current offset
                else:
                    input = input[0:inputoff] + chr(key) + input[inputoff+1:]
    
                # increment the input offset
                inputoff += 1
    
                # scroll right if necessary
                if inputoff - displayoff == width:
                    displayoff += 1


def inputbox(wnd, prompt, field_width, echo=True):
    """Display a window for user input."""

    wnd_height, wnd_width = wnd.getmaxyx()
    height, width = 12, field_width + 7

    # draw a window for the dialog
    childy, childx = center(wnd_height-1, height)+1, center(wnd_width, width)
    child_wnd = wnd.subwin(height, width, childy, childx)
    child_wnd.clear()
    child_wnd.border()

    # draw another window for the text box
    texty, textx = center(height-1, 3)+1, center(width-1, width-5)+1
    textheight, textwidth = 3, width-5
    text_wnd = child_wnd.derwin(textheight, textwidth, texty, textx)
    text_wnd.clear()
    text_wnd.border()
    
    # draw the prompt
    prompty, promptx = 2, 3
    child_wnd.addnstr(prompty, promptx, prompt, width-2)

    # draw the fake buttons
    fakey, fakex = 9, width - 19
    child_wnd.addstr(fakey, fakex, "< OK > < Cancel >")
    child_wnd.addch(fakey, fakex+2, "O", curses.A_UNDERLINE)
    child_wnd.addch(fakey, fakex+9, "C", curses.A_UNDERLINE)

    # update the screen
    child_wnd.noutrefresh()
    text_wnd.noutrefresh()
    curses.doupdate()

    # read an input string within the field region of text_wnd
    inputy, inputx, inputwidth = 1, 1, textwidth - 2
    input = read_input(text_wnd, inputy, inputx, inputwidth, 0, echo)
    
    # erase the window
    child_wnd.erase()
    child_wnd.refresh()

    return input


def line_wrap(line, width):
    """Wrap a string to a certain width (returns a list of strings)."""

    wrapped_lines = []
    tokens = line.split(" ")
    tokens.reverse()
    tmp = tokens.pop()
    if len(tmp) > width:
        wrapped_lines.append(tmp[0:width])
        tmp = tmp[width:]
    while len(tokens) > 0:
        token = tokens.pop()
        if len(tmp) + len(token) + 1 <= width:
            tmp += " " + token
        elif len(token) > width:
            tmp += " " + token[0:width-len(tmp)-1]
            tokens.push(token[width-len(tmp)-1:])
        else:
            wrapped_lines.append(tmp)
            tmp = token
    wrapped_lines.append(tmp)
    return wrapped_lines


def msgbox(wnd, msg, title="Message"):
    """Display a message in a window."""

    # split message into a list of lines
    lines = msg.split("\n")
    
    # determine the dimensions of the method
    message_height = len(lines)
    message_width = 0
    for line in lines:
        if len(line) > message_width:
            message_width = len(line)

    # ensure the window fits the title
    if len(title) > message_width:
        message_width = len(title)

    # maximum message width
    parent_height, parent_width = wnd.getmaxyx()
    max_message_width = parent_width - 8

    # line-wrap if necessary
    if message_width > max_message_width:
        newlines = []
        for line in lines:
            for newline in line_wrap(line, max_message_width):
                newlines.append(newline)
        lines = newlines
        message_width = max_message_width
        message_height = len(lines)

    # random padding that perl's curses adds
    pad_width = 2

    # create the outer window
    outer_height, outer_width = message_height + 8, message_width + pad_width + 6
    outer_y, outer_x = center(parent_height+1, outer_height)-1, center(parent_width, outer_width)
    outer_wnd = wnd.derwin(outer_height, outer_width, outer_y, outer_x)
    outer_wnd.erase()
    outer_wnd.border()

    # create the inner window
    inner_height, inner_width = message_height + 2, message_width + pad_width + 2
    inner_y, inner_x = 2, center(outer_width, inner_width)
    inner_wnd = outer_wnd.derwin(inner_height, inner_width, inner_y, inner_x)
    inner_wnd.border()

    # display the title
    outer_wnd.addstr(0, 1, " " + title + " ", curses.A_REVERSE | curses.A_BOLD)
    
    # display the message
    for i in xrange(len(lines)):
        inner_wnd.addnstr(i+1, 1, lines[i], message_width)

        # draw a solid block at the end of the first few lines
        if i < len(lines) - 1:
            inner_wnd.addch(i+1, inner_width-1, ' ', curses.A_REVERSE)

    # display the fake OK button
    fakey, fakex = outer_height - 3, outer_width - 8
    outer_wnd.addstr(fakey, fakex, "< OK >", curses.A_REVERSE)
    outer_wnd.addch(fakey, fakex+2, "O", curses.A_UNDERLINE | curses.A_REVERSE)

    # update display
    outer_wnd.noutrefresh()
    inner_wnd.noutrefresh()
    curses.doupdate()

    # read a RETURN or ESC before returning
    curses.curs_set(0)
    outer_wnd.keypad(1)
    while True:
        key = outer_wnd.getch(0,0)
        if key == KEY_RETURN or key == KEY_ESCAPE:
            break

    # clear the window
    outer_wnd.erase()
    outer_wnd.refresh()
    

def menu(wnd, offy, offx, width, options, _acquire_wnd=None):
    """
    Draw a menu and wait for a selection.

    Parameters:
        wnd          - parent window
        offy         - vertical offset for menu region
        offx         - horizontal offset for menu region
        width        - width of menu region
        options      - a list of selections
        _acquire_wnd - hack to support resize: must be a function callback
                       that returns new values for wnd, offy, offx, height,
                       width. Unused if None.

    Returns: index into options that was selected
    """

    # the currently selected option
    selected = 0

    while True:
        # disable cursor
        curses.curs_set(0)

        # hack to support resize: recreate the
        # parent window every iteration
        if _acquire_wnd:
            wnd, offy, offx, height, width = _acquire_wnd()

        # keypad mode so getch() works with up, down
        wnd.keypad(1)

        # display the menu
        for i in xrange(len(options)):
            text, callback = options[i]
            text = text + " " * (width - len(text))

            # the selected option is displayed in reverse video
            if i == selected:
                wnd.addstr(i+offy, offx, text, curses.A_REVERSE)
            else:
                wnd.addstr(i+offy, offx, text)
                    # display the member

        wnd.refresh()
        
        # read one keypress
        input = wnd.getch()

        # UP moves to the previous option
        if input == curses.KEY_UP and selected > 0:
            selected = (selected - 1)

        # DOWN moves to the next option
        elif input == curses.KEY_DOWN and selected < len(options) - 1:
            selected = (selected + 1)

        # RETURN runs the callback for the selected option
        elif input == KEY_RETURN:
            text, callback = options[selected]

            # highlight the selected option
            text = text + " " * (width - len(text))
            wnd.addstr(selected+offy, offx, text, curses.A_REVERSE | curses.A_BOLD)
            wnd.refresh()

            # execute the selected option
            if callback(wnd): # success
                break


def reset():
    """Reset the terminal and clear the screen."""

    reset = curses.tigetstr('rs1')
    if not reset: reset = '\x1bc'
    curses.putp(reset)

