#include <stdio.h>
#include <sys/utsname.h>
#include <unistd.h>
#include <netdb.h>
#include <errno.h>

#include "util.h"
#include "net.h"
#include "gss.h"
#include "strbuf.h"

struct strbuf fqdn = STRBUF_INIT;

const size_t MAX_MSGLEN = 65536;
const size_t MSG_BUFINC = 4096;

void setup_fqdn(void) {
    struct utsname uts;
    struct hostent *lo;

    if (uname(&uts))
        fatalpe("uname");
    lo = gethostbyname(uts.nodename);
    if (!lo)
        fatalpe("gethostbyname");

    strbuf_addstr(&fqdn, lo->h_name);
}

void free_fqdn(void) {
    strbuf_release(&fqdn);
}

int ceo_send_message(int sock, void *buf, size_t len, uint32_t msgtype) {
    uint32_t msgheader[2];
    msgheader[0] = htonl(len);
    msgheader[1] = htonl(msgtype);

    if (full_write(sock, msgheader, sizeof(msgheader)) < 0)
        fatalpe("write");

    if (full_write(sock, buf, len) < 0)
        fatalpe("write");

    return 0;
}

int ceo_receive_message(int sock, struct strbuf *msg, uint32_t *msgtype) {
    uint32_t msglen, received = 0;
    uint32_t msgheader[2];
    ssize_t bytes;

    strbuf_reset(msg);

    while (received < sizeof(msgheader)) {
        bytes = read(sock, msgheader, sizeof(msgheader) - received);
        if (bytes < 0) {
            if (errno == EAGAIN)
                continue;
            fatalpe("read");
        }
        if (!bytes && !received)
            return -1;
        if (!bytes)
            fatalpe("short header received");
        received += bytes;
    }

    msglen = ntohl(msgheader[0]);
    *msgtype = ntohl(msgheader[1]);
    received = 0;

    if (!msglen)
        fatal("length is zero in message header");

    if (msglen > MAX_MSGLEN)
        fatal("length is huge in message header");

    strbuf_grow(msg, msglen);
    strbuf_setlen(msg, msglen);

    while (received < msglen) {
        bytes = read(sock, msg->buf + received, msglen - received);
        if (bytes < 0) {
            if (errno == EAGAIN)
                continue;
            fatalpe("read");
        }
        if (!bytes)
            fatal("short message received");
        received += bytes;
    }

    return 0;
}
