CFLAGS ?= -ggdb -Wall -O2
CFLAGS += -I../include

LIBCEO_OBJECTS := util.o common.o config.o parser.o ldap.o krb5.o kadm.o addhomedir.o
LIBCEO_LDFLAGS := -lldap $(shell krb5-config --libs krb5 kadm-client)

DESTDIR :=
PREFIX := /usr/local

all: addmember addclub

clean:
	rm -f addmember addclub zfsaddhomedir config-test *.o

addmember: $(LIBCEO_OBJECTS) addmember.o
	$(CC) $(LDFLAGS) $(LIBCEO_LDFLAGS) $^ -o $@

addclub: $(LIBCEO_OBJECTS) addclub.o
	$(CC) $(LDFLAGS) $(LIBCEO_LDFLAGS) $^ -o $@

zfsaddhomedir: util.o zfsaddhomedir.o
	$(CC) $(LDFLAGS) $^ -o $@

config-test: config-test.o parser.o util.o
	$(CC) $(LDFLAGS) $^ -o $@

install: addmember addclub
	install -d $(DESTDIR)$(PREFIX)/bin
	install addmember addclub $(DESTDIR)$(PREFIX)/bin

