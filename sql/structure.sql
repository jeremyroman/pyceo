-- Table structure for CEO's SQL database.

-- Usage:
--     su postgres
--     createdb ceo
--     psql ceo < structure.sql

CREATE SEQUENCE memberid_seq;

CREATE TABLE members (
        memberid integer PRIMARY KEY DEFAULT nextval('memberid_seq') NOT NULL,
        name character varying(50) NOT NULL,
        studentid character varying(10) UNIQUE,
        program character varying(50),
        "type" character varying(10),
        userid character varying(32) UNIQUE
);


CREATE TABLE terms (
        memberid integer NOT NULL,
        term character(5) NOT NULL,
        UNIQUE(memberid, term)
);
