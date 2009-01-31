CFLAGS   := -g3 -O2 -Wall -Werror -DDEBUG
LDFLAGS  := -L/opt/csw/lib -Wl,-R/opt/csw/lib -L/usr/local/lib -Wl,-R/usr/local/lib
INCLUDES := -I../include $(shell krb5-config --cflags)
override LDFLAGS += -std=gnu99 $(INCLUDES)
override CFLAGS  += -std=gnu99 $(INCLUDES)

DESTDIR :=
PREFIX  := /usr/local

BIN_PROGS := addmember addclub zfsaddhomedir ceod
LIB_PROGS := ceoc
EXT_PROGS := config-test

LIBCEO_OBJECTS := common.o addhomedir.o
LIBCEO_LDFLAGS :=
LIBCEO_PROGS   := addmember addclub
LDAP_OBJECTS   := ldap.o
LDAP_LDFLAGS   := -lldap
LDAP_PROGS     := addmember addclub
KRB5_OBJECTS   := krb5.o kadm.o
KRB5_LDFLAGS   := $(shell krb5-config --libs krb5 kadm-client)
KRB5_PROGS     := addmember addclub
NET_OBJECTS    := net.o gss.o ops.o
NET_LDFLAGS    := -lsctp $(shell krb5-config --libs gssapi)
NET_PROGS      := ceod ceoc
CONFIG_OBJECTS := config.o parser.o
CONFIG_LDFLAGS :=
CONFIG_PROGS   := $(OLDCEO_PROGS) $(LDAP_PROGS) $(KRB5_PROGS) $(NET_PROGS)
UTIL_OBJECTS   := util.o strbuf.o
UTIL_PROGS     := config-test zfsaddhomedir $(CONFIG_PROGS)

all: $(BIN_PROGS) $(LIB_PROGS) $(EXT_PROGS)

clean:
	rm -f $(ALL_PROGS) $(EXT_PROGS) *.o

ceod: dmaster.o dslave.o
	$(CC) $(LDFLAGS) -o $@ $^

config-test: config-test.o parser.o

config.o: config.h config-vars.h

install:
	install -d $(DESTDIR)$(PREFIX)/bin
	install addmember addclub $(DESTDIR)$(PREFIX)/bin

$(NET_PROGS):    LDFLAGS += $(NET_LDFLAGS)
$(NET_PROGS):    $(NET_OBJECTS)
$(LIBCEO_PROGS): LDFLAGS += $(LIBCEO_LDFLAGS)
$(LIBCEO_PROGS): $(LIBCEO_OBJECTS)
$(LDAP_PROGS):   LDFLAGS += $(LDAP_LDFLAGS)
$(LDAP_PROGS):   $(LDAP_OBJECTS)
$(KRB5_PROGS):   LDFLAGS += $(KRB5_LDFLAGS)
$(KRB5_PROGS):   $(KRB5_OBJECTS)
$(CONFIG_PROGS): LDFLAGS += $(CONFIG_LDFLAGS)
$(CONFIG_PROGS): $(CONFIG_OBJECTS)
$(UTIL_PROGS):   LDFLAGS += $(UTIL_LDFLAGS)
$(UTIL_PROGS):   $(UTIL_OBJECTS)

.PHONY: clean all
.SECONDARY: zfsaddhomedir.o addmember.o addclub.o
