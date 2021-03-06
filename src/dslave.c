#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <signal.h>
#include <string.h>
#include <syslog.h>
#include <libgen.h>
#include <getopt.h>
#include <errno.h>
#include <netdb.h>
#include <alloca.h>

#include "util.h"
#include "strbuf.h"
#include "net.h"
#include "config.h"
#include "gss.h"
#include "daemon.h"
#include "ldap.h"
#include "kadm.h"
#include "krb5.h"
#include "ops.h"

static void signal_handler(int sig) {
    if (sig == SIGSEGV) {
        error("segmentation fault");
        signal(sig, SIG_DFL);
        raise(sig);
    } else if (sig != SIGCHLD) {
        fatal("unhandled signal %d", sig);
    }
}

static void setup_slave_sigs(void) {
    struct sigaction sa;
    memset(&sa, 0, sizeof(sa));
    sigemptyset(&sa.sa_mask);
    sa.sa_handler = signal_handler;

    sigaction(SIGCHLD, &sa, NULL);
    sigaction(SIGSEGV, &sa, NULL);

    signal(SIGINT,  SIG_DFL);
    signal(SIGTERM, SIG_DFL);
    signal(SIGPIPE, SIG_IGN);

    if (terminate)
        raise(fatal_signal);
}

static void handle_auth_message(struct strbuf *in, struct strbuf *out) {
    gss_buffer_desc incoming_tok, outgoing_tok;
    OM_uint32 maj_stat, min_stat;

    incoming_tok.value = in->buf;
    incoming_tok.length = in->len;

    process_server_token(&incoming_tok, &outgoing_tok);

    strbuf_add(out, outgoing_tok.value, outgoing_tok.length);

    if (outgoing_tok.length) {
        maj_stat = gss_release_buffer(&min_stat, &outgoing_tok);
        if (maj_stat != GSS_S_COMPLETE)
            gss_fatal("gss_release_buffer", maj_stat, min_stat);
    }
}

static void handle_op_message(uint32_t in_type, struct strbuf *in, struct strbuf *out) {
    struct op *op = get_local_op(in_type);
    struct strbuf in_plain = STRBUF_INIT, out_plain = STRBUF_INIT;
    char *envp[16];

    if (!op)
        fatal("operation %x does not exist", in_type);

    debug("running op: %s", op->name);

    /* TEMPORARY */
    if (!client_username())
        fatal("unathenticated");

    gss_decipher(in, &in_plain);

    make_env(envp, "LANG", "C", "CEO_USER", client_username(),
                   "CEO_CONFIG_DIR", config_dir, NULL);
    char *argv[] = { op->path, NULL, };

    if (spawnvemu(op->path, argv, envp, &in_plain, &out_plain, 0, op->user))
        fatal("child %s failed", op->path);

    gss_encipher(&out_plain, out);

    if (!out->len)
        fatal("no response from op");

    free_env(envp);
    strbuf_release(&in_plain);
    strbuf_release(&out_plain);
}

static void handle_one_message(int sock, struct strbuf *in, uint32_t msgtype) {
    struct strbuf out = STRBUF_INIT;

    if (msgtype == MSG_AUTH)
        handle_auth_message(in, &out);
    else
        handle_op_message(msgtype, in, &out);

    if (out.len && ceo_send_message(sock, out.buf, out.len, msgtype))
        fatalpe("write");

    strbuf_release(&out);
}

void slave_main(int sock, struct sockaddr *addr) {
    char addrstr[INET_ADDRSTRLEN];
    struct sockaddr_in *addr_in = (struct sockaddr_in *)addr;
    uint32_t msgtype;
    struct strbuf msg = STRBUF_INIT;

    if (addr->sa_family != AF_INET)
        fatal("unsupported address family %d", addr->sa_family);

    if (!inet_ntop(AF_INET, &addr_in->sin_addr, addrstr, sizeof(addrstr)))
        fatalpe("inet_ntop");

    notice("accepted connection from %s", addrstr);

    setup_slave_sigs();

    while (!terminate) {
        if (ceo_receive_message(sock, &msg, &msgtype))
            break;
        handle_one_message(sock, &msg, msgtype);
    }

    notice("connection closed by peer %s", addrstr);

    strbuf_release(&msg);

    /* stuff allocated by dmaster */
    free_gss();
    free_config();
    free_fqdn();
    free_ops();
    free(prog);
}

