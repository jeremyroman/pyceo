"""Library Routines"""

def read_config(config_file):

    try:
        conffile = open(config_file)
    except IOError:
        return None
    
    options = {}

    while True:

        line = conffile.readline()
        if line == '':
            break

        if '#' in line:
            line = line[:line.find('#')]

        while len(line) > 1 and line[-2] == '\\':
            line = line[:-2] + line[-1]
            next = conffile.readline()
            line += next
            if next == '':
                break

        pair = map(str.strip, line.split('=', 1))
        
        if len(pair) == 2:
            key, val = pair

            if val[0] == val[-1] == '"':
                val = val[1:-1]
            else:
                try:
                    val = int(val)
                except:
                    pass
            
            options[key] = val
        elif len(pair[0]) > 1:
            key, = pair
            options[key] = None

    return options
