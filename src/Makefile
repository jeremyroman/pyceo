CFLAGS   := -g3 -O2 -Wall -Werror -DDEBUG
LDFLAGS  := -Wl,--as-needed
INCLUDES := $(shell krb5-config --cflags)
override CFLAGS  += -std=gnu99 $(INCLUDES)

DESTDIR :=
PREFIX  := /usr/local

BIN_PROGS := addmember addclub ceod
LIB_PROGS := ceoc op-adduser
EXT_PROGS := config-test

LDAP_OBJECTS   := ldap.o
LDAP_LIBS      := -lldap
LDAP_PROGS     := op-adduser
KRB5_OBJECTS   := krb5.o kadm.o
KRB5_LIBS      := $(shell krb5-config --libs krb5 kadm-client)
KRB5_PROGS     := addmember addclub op-adduser
HOME_OBJECTS   := homedir.o
HOME_LIBS      := -lacl
HOME_PROGS     := op-adduser
NET_OBJECTS    := net.o gss.o ops.o
NET_LIBS       := -lsctp $(shell krb5-config --libs gssapi)
NET_PROGS      := ceod ceoc
PROTO_OBJECTS  := ceo.pb-c.o
PROTO_LIBS     := -lprotobuf-c
PROTO_PROGS    := op-adduser addmember addclub
CONFIG_OBJECTS := config.o parser.o
CONFIG_LIBS    :=
CONFIG_PROGS   := $(LDAP_PROGS) $(KRB5_PROGS) $(NET_PROGS)
UTIL_OBJECTS   := util.o strbuf.o
UTIL_PROGS     := config-test $(CONFIG_PROGS)

all: $(BIN_PROGS) $(LIB_PROGS) $(EXT_PROGS) ../ceo/ceo_pb2.py

clean:
	rm -f $(BIN_PROGS) $(LIB_PROGS) $(EXT_PROGS) *.o ceo.pb-c.c ceo.pb-c.h

op-adduser.o addmember.o addclub.o: ceo.pb-c.h

ceo.pb-c.c ceo.pb-c.h: ceo.proto
	protoc-c --c_out=. ceo.proto

%: %.o
	$(CC) $(CFLAGS) $(LDFLAGS) $^ $(LDLIBS) -o $@

../ceo/ceo_pb2.py:
	protoc --python_out=../ceo ceo.proto

ceod: dmaster.o dslave.o
	$(CC) $(CFLAGS) $(LDFLAGS) $^ $(LDLIBS) -o $@

config-test: config-test.o parser.o

config.o: config.h config-vars.h

install_clients:
	install -d $(DESTDIR)$(PREFIX)/bin $(DESTDIR)$(PREFIX)/lib/ceod
	install addmember addclub $(DESTDIR)$(PREFIX)/bin
	install ceoc $(DESTDIR)$(PREFIX)/lib/ceod

install_daemon:
	install -d $(DESTDIR)$(PREFIX)/sbin $(DESTDIR)$(PREFIX)/lib/ceod
	install ceod $(DESTDIR)$(PREFIX)/sbin
	install op-adduser $(DESTDIR)$(PREFIX)/lib/ceod

install: install_clients install_daemon

$(NET_PROGS):    LDLIBS += $(NET_LIBS)
$(NET_PROGS):    $(NET_OBJECTS)
$(LDAP_PROGS):   LDLIBS += $(LDAP_LIBS)
$(LDAP_PROGS):   $(LDAP_OBJECTS)
$(KRB5_PROGS):   LDLIBS += $(KRB5_LIBS)
$(KRB5_PROGS):   $(KRB5_OBJECTS)
$(HOME_PROGS):   LDLIBS += $(HOME_LIBS)
$(HOME_PROGS):   $(HOME_OBJECTS)
$(PROTO_PROGS):  LDLIBS += $(PROTO_LIBS)
$(PROTO_PROGS):  $(PROTO_OBJECTS)
$(CONFIG_PROGS): LDLIBS += $(CONFIG_LIBS)
$(CONFIG_PROGS): $(CONFIG_OBJECTS)
$(UTIL_PROGS):   LDLIBS += $(UTIL_LIBS)
$(UTIL_PROGS):   $(UTIL_OBJECTS)

.PHONY: clean all install install_clients install_daemon
