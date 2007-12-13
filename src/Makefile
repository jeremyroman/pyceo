CFLAGS ?= -ggdb -Wall -O2
CFLAGS += -I../include
LDAP := -lldap
KADM := $(shell krb5-config --libs krb5 kadm-client)

LIBCEO := util.o common.o config.o parser.o ldap.o krb5.o kadm.o addhomedir.o

DESTDIR :=
PREFIX := /usr/local

all: addmember addclub

clean:
	rm -f addmember addclub config-test *.o

addmember: $(LIBCEO) addmember.o
	$(CC) $(LDFLAGS) $(LDAP) $(KADM) $^ -o $@

addclub: $(LIBCEO) addclub.o
	$(CC) $(LDFLAGS) $(LDAP) $(KADM) $^ -o $@

config-test: config-test.o parser.o util.o
	$(CC) $(LDFLAGS) $^ -o $@

install: addmember addclub
	install -d $(DESTDIR)$(PREFIX)/bin
	install addmember addclub $(DESTDIR)$(PREFIX)/bin

