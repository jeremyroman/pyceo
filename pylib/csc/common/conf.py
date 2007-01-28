"""
Configuration Utility Module

This module contains functions to load and verify very simple configuration
files. Python supports ".ini" files, which suck, so this module is used
instead.

Example Configuration File:

    include /path/to/other.cf

    # these values are the same:
    name_protected = "Michael Spang"
    name_unprotected = Michael Spang
    
    # these values are not the same:
    yes_no = " yes"
    no_yes =  yes
    
    # this value is an integer
    arbitrary_number=2
    
    # this value is not an integer
    arbitrary_string="2"
    
    # this is a key with no value
    csclub

    # this key contains whitespace
    white space = sure, why not

    # these two lines are treated as one
    long line = first line \
                second line

Resultant Dictionary:

    {
      'name_protected': 'Michael Spang',
      'name_unprotected:' 'Michael Spang',
      'yes_no': ' yes',
      'no_yes': 'yes',
      'arbirary_number': 2,
      'arbitrary_string': '2',
      'csclub': None,
      'white space': 'sure, why not'
      'long line': 'first line \n               second line' 
      
      ... (data from other.cf) ...
    }

"""
from curses.ascii import isspace


class ConfigurationException(Exception):
    """Exception class for incomplete and incorrect configurations."""
    

def read(filename, included=None):
    """Function to read a configuration file into a dictionary."""

    if not included:
        included = []
    if filename in included:
        return {}
    included.append(filename)

    try:
        conffile = open(filename)
    except IOError:
        raise ConfigurationException('unable to read configuration file: "%s"' % filename)
    
    options = {}

    while True:

        line = conffile.readline()
        if line == '':
            break

        # remove comments
        if '#' in line:
            line = line[:line.find('#')]

        # combine lines when the newline is escaped with \
        while len(line) > 1 and line[-2] == '\\':
            line = line[:-2] + line[-1]
            next = conffile.readline()
            line += next
            if next == '':
                break

        line = line.strip()

        # process include statements
        if line.find("include") == 0 and isspace(line[7]):

            filename = line[8:].strip()
            options.update(read(filename, included))
            continue

        # split 'key = value' into key and value and strip results
        pair = map(str.strip, line.split('=', 1))
        
        # found key and value
        if len(pair) == 2:
            key, val = pair

            # found quoted string?
            if val[0] == val[-1] == '"':
                val = val[1:-1]

            # unquoted, found float?
            else:
                try:
                    if "." in val:
                        val = float(val)
                    else:
                        val = int(val)
                except ValueError:
                    pass
            
            # save key and value
            options[key] = val

        # found only key, value = None
        elif len(pair[0]) > 1:
            key = pair[0]
            options[key] = None

    return options


def check_string_fields(filename, field_list, cfg):
    """Function to verify thatfields are strings."""

    for field in field_list:
        if field not in cfg or type(cfg[field]) is not str:
            raise ConfigurationException('expected string value for option "%s" in "%s"' % (field, filename))

def check_integer_fields(filename, field_list, cfg):
    """Function to verify that fields are integers."""

    for field in field_list:
        if field not in cfg or type(cfg[field]) not in (int, long):
            raise ConfigurationException('expected numeric value for option "%s" in "%s"' % (field, filename))

def check_float_fields(filename, field_list, cfg):
    """Function to verify that fields are integers or floats."""

    for field in field_list:
        if field not in cfg or type(cfg[field]) not in (float, long, int):
            raise ConfigurationException('expected float value for option "%s" in "%s"' % (field, filename))
