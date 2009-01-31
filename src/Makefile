CFLAGS   := -g3 -O2 -Wall -Werror -DDEBUG
LDFLAGS  := -L/opt/csw/lib -Wl,-R/opt/csw/lib -L/usr/local/lib -Wl,-R/usr/local/lib
INCLUDES := -I../include $(shell krb5-config --cflags)
override LDFLAGS += -std=gnu99 $(INCLUDES)
override CFLAGS  += -std=gnu99 $(INCLUDES)

DESTDIR :=
PREFIX  := /usr/local

BIN_PROGS := addmember addclub zfsaddhomedir ceod
LIB_PROGS := ceoc op-adduser
EXT_PROGS := config-test

LDAP_OBJECTS   := ldap.o
LDAP_LDFLAGS   := -lldap
LDAP_PROGS     := addmember addclub op-adduser
KRB5_OBJECTS   := krb5.o kadm.o
KRB5_LDFLAGS   := $(shell krb5-config --libs krb5 kadm-client)
KRB5_PROGS     := addmember addclub op-adduser
NET_OBJECTS    := net.o gss.o ops.o
NET_LDFLAGS    := -lsctp $(shell krb5-config --libs gssapi)
NET_PROGS      := ceod ceoc
PROTO_OBJECTS  := ceo.pb-c.o
PROTO_LDFLAGS  := -lprotobuf-c
PROTO_PROGS    := op-adduser addmember addclub
CONFIG_OBJECTS := config.o parser.o
CONFIG_LDFLAGS :=
CONFIG_PROGS   := $(LDAP_PROGS) $(KRB5_PROGS) $(NET_PROGS)
UTIL_OBJECTS   := util.o strbuf.o
UTIL_PROGS     := config-test zfsaddhomedir $(CONFIG_PROGS)

all: $(BIN_PROGS) $(LIB_PROGS) $(EXT_PROGS)

clean:
	rm -f $(BIN_PROGS) $(LIB_PROGS) $(EXT_PROGS) *.o ceo.pb-c.c ceo.pb-c.h

op-adduser.o addmember.o addclub.o: ceo.pb-c.h

ceo.pb-c.c ceo.pb-c.h: ceo.proto
	protoc-c --c_out=. ceo.proto

ceod: dmaster.o dslave.o
	$(CC) $(LDFLAGS) -o $@ $^

config-test: config-test.o parser.o

config.o: config.h config-vars.h

install:
	install -d $(DESTDIR)$(PREFIX)/sbin $(DESTDIR)$(PREFIX)/bin $(DESTDIR)$(PREFIX)/lib/ceod
	install ceod $(DESTDIR)$(PREFIX)/sbin
	install addmember addclub $(DESTDIR)$(PREFIX)/bin
	install ceoc op-adduser $(DESTDIR)$(PREFIX)/lib/ceod

$(NET_PROGS):    LDFLAGS += $(NET_LDFLAGS)
$(NET_PROGS):    $(NET_OBJECTS)
$(LDAP_PROGS):   LDFLAGS += $(LDAP_LDFLAGS)
$(LDAP_PROGS):   $(LDAP_OBJECTS)
$(KRB5_PROGS):   LDFLAGS += $(KRB5_LDFLAGS)
$(KRB5_PROGS):   $(KRB5_OBJECTS)
$(PROTO_PROGS):  LDFLAGS += $(PROTO_LDFLAGS)
$(PROTO_PROGS):  $(PROTO_OBJECTS)
$(CONFIG_PROGS): LDFLAGS += $(CONFIG_LDFLAGS)
$(CONFIG_PROGS): $(CONFIG_OBJECTS)
$(UTIL_PROGS):   LDFLAGS += $(UTIL_LDFLAGS)
$(UTIL_PROGS):   $(UTIL_OBJECTS)

.PHONY: clean all
.SECONDARY: ceoc.o zfsaddhomedir.o addmember.o addclub.o
