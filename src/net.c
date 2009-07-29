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

static size_t recv_one_message(int sock, struct sctp_meta *msg_meta, struct strbuf *msg, int *notification) {
    size_t len = 0;
    int flags = 0;
    int bytes;

    strbuf_reset(msg);

    do {
        msg_meta->fromlen = sizeof(msg_meta->from);

        bytes = sctp_recvmsg(sock, msg->buf + len, strbuf_avail(msg) - len,
                             (sa *)&msg_meta->from, &msg_meta->fromlen, &msg_meta->sinfo, &flags);

        if (bytes < 0) {
            if (errno == EAGAIN)
                continue;
            fatalpe("sctp_recvmsg");
        }
        if (!bytes)
            break;
        len += bytes;

        if (msg->len > MAX_MSGLEN)
            fatal("oversized message received");
        if (strbuf_avail(msg) < MSG_BUFINC)
            strbuf_grow(msg, MSG_BUFINC);

    } while (~flags & MSG_EOR);

    if (!bytes && len)
        fatalpe("EOF in the middle of a message");

    *notification = flags & MSG_NOTIFICATION;
    if (*notification) {
        notification_dbg(msg->buf);
        union sctp_notification *sn = (union sctp_notification *) msg->buf;
        switch (sn->sn_header.sn_type) {
            case SCTP_SHUTDOWN_EVENT:
                fatal("connection shut down");
                break;
            case SCTP_ASSOC_CHANGE:
                switch (sn->sn_assoc_change.sac_state) {
                    case SCTP_COMM_LOST:
                        fatal("connection lost");
                        break;
                    case SCTP_SHUTDOWN_COMP:
                        fatal("shutdown complete");
                        break;
                    case SCTP_CANT_STR_ASSOC:
                        fatal("cannot start association");
                        break;
                }
                break;
        }
    }

    strbuf_setlen(msg, len);
    return len;
}

int receive_one_message(int sock, struct sctp_meta *msg_meta, struct strbuf *msg) {
    int notification = 0;

    do {
        recv_one_message(sock, msg_meta, msg, &notification);
    } while (notification);

    return msg->len > 0;
}

void notification_dbg(char *notification) {
    union sctp_notification *sn = (union sctp_notification *) notification;
    char *extra;

    switch (sn->sn_header.sn_type) {
        case SCTP_ASSOC_CHANGE:
            extra = "unknown state";
            switch (sn->sn_assoc_change.sac_state) {
                case SCTP_COMM_UP: extra = "established"; break;
                case SCTP_COMM_LOST: extra = "lost"; break;
                case SCTP_RESTART: extra = "restarted"; break;
                case SCTP_SHUTDOWN_COMP: extra = "completed shutdown"; break;
                case SCTP_CANT_STR_ASSOC: extra = "cannot start"; break;
            }
            debug("association changed: association 0x%x %s", sn->sn_assoc_change.sac_assoc_id, extra);
            break;
        case SCTP_PEER_ADDR_CHANGE:
            extra = "unknown state";
            switch (sn->sn_paddr_change.spc_state) {
                case SCTP_ADDR_AVAILABLE: extra = "unavailable"; break;
                case SCTP_ADDR_UNREACHABLE: extra = "unreachable"; break;
                case SCTP_ADDR_REMOVED: extra = "removed"; break;
                case SCTP_ADDR_ADDED: extra = "added"; break;
                case SCTP_ADDR_MADE_PRIM: extra = "made primary"; break;
#ifdef SCTP_ADDR_CONFIRMED
                case SCTP_ADDR_CONFIRMED: extra = "confirmed"; break;
#endif
            }

            struct sockaddr_in *sa = (struct sockaddr_in *) &sn->sn_paddr_change.spc_aaddr;
            char addr[INET_ADDRSTRLEN];
            inet_ntop(AF_INET, &sa->sin_addr, addr, sizeof(addr));
            debug("peer address change: remote address %s %s", addr, extra);
            break;
        case SCTP_REMOTE_ERROR:
            debug("remote error: association=0x%x error=0x%x",
                    sn->sn_remote_error.sre_assoc_id,
                    sn->sn_remote_error.sre_error);
            break;
        case SCTP_SEND_FAILED:
            debug("send failed: association=0x%x error=0x%x",
                    sn->sn_send_failed.ssf_assoc_id,
                    sn->sn_send_failed.ssf_error);
            break;
        case SCTP_ADAPTATION_INDICATION:
            debug("adaptation indication: 0x%x",
                    sn->sn_adaptation_event.sai_adaptation_ind);
            break;
        case SCTP_PARTIAL_DELIVERY_EVENT:
            extra = "unknown indication";
            switch (sn->sn_pdapi_event.pdapi_indication) {
                case SCTP_PARTIAL_DELIVERY_ABORTED:
                    extra = "partial delivery aborted";
                    break;
            }
            debug("partial delivery event: %s", extra);
            break;
        case SCTP_SHUTDOWN_EVENT:
            debug("association 0x%x was shut down",
                    sn->sn_shutdown_event.sse_assoc_id);
            break;
        default:
            debug("unknown sctp notification type 0x%x\n",
                    sn->sn_header.sn_type);
    }
}
