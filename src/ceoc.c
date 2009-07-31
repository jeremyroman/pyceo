#include <string.h>
#include <stdio.h>
#include <unistd.h>
#include <getopt.h>
#include <libgen.h>

#include "util.h"
#include "net.h"
#include "gss.h"
#include "ops.h"
#include "config.h"

char *prog = NULL;

static struct option opts[] = {
    { NULL, 0, NULL, '\0' },
};

static void usage() {
    fprintf(stderr, "Usage: %s op\n", prog);
    exit(2);
}

static void send_gss_token(int sock, struct sockaddr *addr, socklen_t addrlen, gss_buffer_t token) {
    OM_uint32 maj_stat, min_stat;

    if (sctp_sendmsg(sock, token->value, token->length,
                     addr, addrlen, MSG_AUTH, 0, 0, 0, 0) < 0)
        fatalpe("sctp_sendmsg");

    maj_stat = gss_release_buffer(&min_stat, token);
    if (maj_stat != GSS_S_COMPLETE)
        gss_fatal("gss_release_buffer", maj_stat, min_stat);
}

static void client_gss_auth(int sock, struct sockaddr *addr, socklen_t addrlen) {
    gss_buffer_desc incoming_tok, outgoing_tok;
    struct sctp_meta msg_meta;
    struct strbuf msg = STRBUF_INIT;
    int complete;

    complete = initial_client_token(&outgoing_tok);

    for (;;) {
        if (outgoing_tok.length)
            send_gss_token(sock, addr, addrlen, &outgoing_tok);
        else if (!complete)
            fatal("no token to send during auth");

        if (complete)
            break;

        if (!receive_one_message(sock, &msg_meta, &msg))
            fatal("connection closed during auth");

        if (msg_meta.sinfo.sinfo_ppid != MSG_AUTH)
            fatal("unexpected message type 0x%x", msg_meta.sinfo.sinfo_ppid);

        incoming_tok.value = msg.buf;
        incoming_tok.length = msg.len;

        complete = process_client_token(&incoming_tok, &outgoing_tok);
    }

    strbuf_release(&msg);
}

void run_remote(struct op *op, struct strbuf *in, struct strbuf *out) {
    const char *hostname = op->hostname;
    int sock = socket(PF_INET, SOCK_SEQPACKET, IPPROTO_SCTP);
    struct sockaddr_in addr;
    struct sctp_meta response_meta;

    if (!in->len)
        fatal("no data to send");

    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(9987);
    addr.sin_addr = op->addr;

    struct sctp_event_subscribe events;
    memset(&events, 0, sizeof(events));
    events.sctp_data_io_event = 1;
    events.sctp_association_event = 1;
    events.sctp_address_event = 1;
    events.sctp_send_failure_event = 1;
    events.sctp_peer_error_event = 1;
    events.sctp_shutdown_event = 1;
    events.sctp_partial_delivery_event = 1;
    events.sctp_adaptation_layer_event = 1;

    if (setsockopt(sock, IPPROTO_SCTP, SCTP_EVENTS, &events, sizeof(events)))
        fatalpe("setsockopt");

    client_acquire_creds("ceod", hostname);
    client_gss_auth(sock, (sa *)&addr, sizeof(addr));

    if (sctp_sendmsg(sock, in->buf, in->len, (struct sockaddr *)&addr,
                     sizeof(addr), op->id, 0, 0, 0, 0) < 0)
        fatalpe("sctp_sendmsg");

    if (!receive_one_message(sock, &response_meta, out))
        fatal("no response received for op %s", op->name);

    if (response_meta.sinfo.sinfo_ppid != op->id)
        fatal("wrong ppid from server: expected %d got %d", op->id, response_meta.sinfo.sinfo_ppid);

    if (sctp_sendmsg(sock, NULL, 0, (struct sockaddr *)&addr,
                sizeof(addr), 0, SCTP_EOF, 0, 0 ,0) < 0)
        fatalpe("sctp_sendmsg");
}

int client_main(char *op_name) {
    struct op *op = find_op(op_name);

    if (!op)
        fatal("no such op: %s", op_name);

    struct strbuf in = STRBUF_INIT;
    struct strbuf out = STRBUF_INIT;

    if (strbuf_read(&in, STDIN_FILENO, 0) < 0)
        fatalpe("read");

    run_remote(op, &in, &out);

    if (strbuf_write(&out, STDOUT_FILENO) < 0)
        fatalpe("write");

    strbuf_release(&in);
    strbuf_release(&out);

    return 0;
}

int main(int argc, char *argv[]) {
    int opt;
    int ret;
    char *op;

    prog = xstrdup(basename(argv[0]));
    init_log(prog, LOG_PID, LOG_USER);

    configure();
    setup_ops();
    setup_fqdn();

    while ((opt = getopt_long(argc, argv, "", opts, NULL)) != -1) {
        switch (opt) {
            case '?':
                usage();
                break;
            default:
                fatal("error parsing arguments");
        }
    }

    if (argc - optind != 1)
        usage();

    op = argv[optind++];

    ret = client_main(op);

    free_gss();
    free_fqdn();
    free_config();
    free_ops();
    free(prog);

    return ret;
}
