-- PL/Python trigger to verify student ids for validity
-- Dedicated to office staff who can't type student ids.

-- To (re)install:
--     su postgres
--     psql ceo < verify_studentid.sql

-- To uninstall:
--     su postgres
--     echo 'DROP FUNCTION verify_studentid() CASCADE' | psql ceo

DROP FUNCTION verify_studentid() CASCADE;

CREATE FUNCTION verify_studentid() RETURNS trigger AS '
    import re

    # update this line if the student id format changes
    STUDENTID_REGEX = "^[0-9]{8}$"
    
    studentid = TD["new"]["studentid"]
    if studentid and not re.match(STUDENTID_REGEX, studentid):
    	plpy.error("student id is invalid (%s)" % studentid)

' LANGUAGE plpythonu;

CREATE TRIGGER verify_studentid_insert BEFORE INSERT on members
    FOR ROW EXECUTE PROCEDURE verify_studentid();

CREATE TRIGGER verify_studentid_update BEFORE UPDATE ON members
    FOR ROW EXECUTE PROCEDURE verify_studentid();
