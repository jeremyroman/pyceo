CFLAGS   := -g3 -O2 -Wall -Werror -DDEBUG
LDFLAGS  := -L/opt/csw/lib -Wl,-R/opt/csw/lib -L/usr/local/lib -Wl,-R/usr/local/lib
INCLUDES := -I../include $(shell krb5-config --cflags)
override LDFLAGS += -std=gnu99 $(INCLUDES)
override CFLAGS  += -std=gnu99 $(INCLUDES)

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

config.o: config.h config-vars.h

install: addmember addclub
	install -d $(DESTDIR)$(PREFIX)/bin
	install addmember addclub $(DESTDIR)$(PREFIX)/bin

