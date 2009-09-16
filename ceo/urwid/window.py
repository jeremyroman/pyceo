import urwid

window_stack = []
window_names = []

header = urwid.Text( "" )
footer = urwid.Text( "" )

ui = urwid.curses_display.Screen()

ui.register_palette([
    # name, foreground, background, mono
    ('banner', 'light gray', 'default', None),
    ('menu', 'light gray', 'default', 'bold'),
    ('selected', 'black', 'light gray', 'bold'),
])

top = urwid.Frame( urwid.SolidFill(), header, footer )

def push_window( frame, name=None ):
    window_stack.append( frame )
    window_names.append( name )
    update_top()

def pop_window():
    if len(window_stack) == 1:
       return False
    window_stack.pop()
    window_names.pop()
    update_top()
    clear_status()
    return True

def update_top():
    names = [ n for n in window_names if n ]
    header.set_text(" - ".join( names ) + "\n")
    top.set_body( window_stack[-1] )

def set_status(message):
    footer.set_text(message)

def clear_status():
    footer.set_text("")

class Abort(Exception):
    pass

class Back(Exception):
    pass

def raise_abort(*args, **kwargs):
    raise Abort()

def raise_back(*args, **kwarg):
    raise Back()

def redraw():
   cols, rows = ui.get_cols_rows()
   canvas = top.render( (cols, rows), focus=True )
   ui.draw_screen( (cols, rows), canvas )
   return cols, rows

def event_loop(ui):
    while True:
        try:
           cols, rows = redraw()

           keys = ui.get_input()
           for k in keys:
              if k == "esc":
                 if not pop_window():
                     break
              elif k == "window resize":
                 (cols, rows) = ui.get_cols_rows()
              else:
                 top.keypress( (cols, rows), k )
        except Back:
            pop_window()
        except (Abort, KeyboardInterrupt):
            return
