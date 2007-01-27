-- $Id$
-- PL/Python trigger to verify terms for validity

-- To (re)install:
--     su postgres
--     psql ceo < verify_term.sql

-- To uninstall:
--     su postgres
--     echo 'DROP FUNCTION verify_term() CASCADE' | psql ceo

DROP FUNCTION verify_term() CASCADE;

CREATE FUNCTION verify_term() RETURNS trigger AS '
    import re

    # update this line if the term format changes
    TERM_REGEX = "^[wsf][0-9]{4}$"
    
    term = TD["new"]["term"]
    if term and not re.match(TERM_REGEX, term):
    	plpy.error("term is invalid (%s)" % term)

' LANGUAGE plpythonu;

CREATE TRIGGER verify_term_insert BEFORE INSERT on terms
    FOR ROW EXECUTE PROCEDURE verify_term();

CREATE TRIGGER verify_term_update BEFORE UPDATE ON terms
    FOR ROW EXECUTE PROCEDURE verify_term();
