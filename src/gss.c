#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <grp.h>

#include "util.h"
#include "gss.h"
#include "net.h"
#include "strbuf.h"

static gss_cred_id_t my_creds = GSS_C_NO_CREDENTIAL;
static gss_ctx_id_t context_handle = GSS_C_NO_CONTEXT;
static gss_name_t peer_name = GSS_C_NO_NAME;
static gss_name_t imported_service = GSS_C_NO_NAME;
static gss_OID mech_type = GSS_C_NO_OID;
static gss_buffer_desc peer_principal;
static char *peer_username;
static OM_uint32 ret_flags;
static int complete;
char service_name[128];

static void display_status(char *prefix, OM_uint32 code, int type) {
    OM_uint32 maj_stat, min_stat;
    gss_buffer_desc msg;
    OM_uint32 msg_ctx = 0;

    maj_stat = gss_display_status(&min_stat, code, type, GSS_C_NULL_OID,
                                  &msg_ctx, &msg);
    logmsg(LOG_ERR, "%s: %s", prefix, (char *)msg.value);
    gss_release_buffer(&min_stat, &msg);

    while (msg_ctx) {
        maj_stat = gss_display_status(&min_stat, code, type, GSS_C_NULL_OID,
                                      &msg_ctx, &msg);
        logmsg(LOG_ERR, "additional: %s", (char *)msg.value);
        gss_release_buffer(&min_stat, &msg);
    }
}

void gss_fatal(char *msg, OM_uint32 maj_stat, OM_uint32 min_stat) {
    logmsg(LOG_ERR, "fatal: %s", msg);
    display_status("major", maj_stat, GSS_C_GSS_CODE);
    display_status("minor", min_stat, GSS_C_MECH_CODE);
    exit(1);
}

static void import_service(const char *service, const char *hostname) {
    OM_uint32 maj_stat, min_stat;
    gss_buffer_desc buf_desc;

    if (snprintf(service_name, sizeof(service_name),
                 "%s@%s", service, hostname) >= sizeof(service_name))
        fatal("service name too long");

    buf_desc.value = service_name;
    buf_desc.length = strlen(service_name);

    maj_stat = gss_import_name(&min_stat, &buf_desc,
                               GSS_C_NT_HOSTBASED_SERVICE, &imported_service);
    if (maj_stat != GSS_S_COMPLETE)
        gss_fatal("gss_import_name", maj_stat, min_stat);
}

static void check_services(OM_uint32 flags) {
    debug("gss services: %sconf %sinteg %smutual %sreplay %ssequence",
            flags & GSS_C_CONF_FLAG     ? "+" : "-",
            flags & GSS_C_INTEG_FLAG    ? "+" : "-",
            flags & GSS_C_MUTUAL_FLAG   ? "+" : "-",
            flags & GSS_C_REPLAY_FLAG   ? "+" : "-",
            flags & GSS_C_SEQUENCE_FLAG ? "+" : "-");
    if (~flags & GSS_C_CONF_FLAG)
        fatal("confidentiality service required");
    if (~flags & GSS_C_INTEG_FLAG)
        fatal("integrity service required");
    if (~flags & GSS_C_MUTUAL_FLAG)
        fatal("mutual authentication required");
}

void server_acquire_creds(const char *service) {
    OM_uint32 maj_stat, min_stat;
    OM_uint32 time_rec;

    if (!strlen(fqdn.buf))
        fatal("empty fqdn");

    import_service(service, fqdn.buf);

    notice("acquiring credentials for %s", service_name);

    maj_stat = gss_acquire_cred(&min_stat, imported_service, GSS_C_INDEFINITE,
                                GSS_C_NULL_OID_SET, GSS_C_ACCEPT, &my_creds,
                                NULL, &time_rec);
    if (maj_stat != GSS_S_COMPLETE)
        gss_fatal("gss_acquire_cred", maj_stat, min_stat);

    if (time_rec != GSS_C_INDEFINITE)
        fatal("credentials valid for %d seconds (oops)", time_rec);
}

void client_acquire_creds(const char *service, const char *hostname) {
    import_service(service, hostname);
}

int process_server_token(gss_buffer_t incoming_tok, gss_buffer_t outgoing_tok) {
    OM_uint32 maj_stat, min_stat;
    OM_uint32 time_rec;
    gss_OID name_type;

    if (complete)
        fatal("unexpected %zd-byte token from peer", incoming_tok->length);

    maj_stat = gss_accept_sec_context(&min_stat, &context_handle, my_creds,
            incoming_tok, GSS_C_NO_CHANNEL_BINDINGS, &peer_name, &mech_type,
            outgoing_tok, &ret_flags, &time_rec, NULL);
    if (maj_stat == GSS_S_COMPLETE) {
        check_services(ret_flags);

        complete = 1;

        maj_stat = gss_display_name(&min_stat, peer_name, &peer_principal, &name_type);
        if (maj_stat != GSS_S_COMPLETE)
            gss_fatal("gss_display_name", maj_stat, min_stat);

        notice("client authenticated as %s", (char *)peer_principal.value);
        debug("context expires in %d seconds",time_rec);

    } else if (maj_stat != GSS_S_CONTINUE_NEEDED) {
        gss_fatal("gss_accept_sec_context", maj_stat, min_stat);
    }

    return complete;
}

int process_client_token(gss_buffer_t incoming_tok, gss_buffer_t outgoing_tok) {
    OM_uint32 maj_stat, min_stat;
    OM_uint32 time_rec;
    gss_OID_desc krb5 = *gss_mech_krb5;

    if (complete)
        fatal("unexpected token from peer");

    maj_stat = gss_init_sec_context(&min_stat, GSS_C_NO_CREDENTIAL, &context_handle,
                                    imported_service, &krb5, GSS_C_MUTUAL_FLAG |
                                    GSS_C_REPLAY_FLAG | GSS_C_SEQUENCE_FLAG,
                                    GSS_C_INDEFINITE, GSS_C_NO_CHANNEL_BINDINGS,
                                    incoming_tok, NULL, outgoing_tok, &ret_flags,
                                    &time_rec);
    if (maj_stat == GSS_S_COMPLETE) {
        notice("server authenticated as %s", service_name);
        notice("context expires in %d seconds", time_rec);

        check_services(ret_flags);

        complete = 1;

    } else if (maj_stat != GSS_S_CONTINUE_NEEDED) {
        gss_fatal("gss_init_sec_context", maj_stat, min_stat);
    }

    return complete;
}

int initial_client_token(gss_buffer_t outgoing_tok) {
    return process_client_token(GSS_C_NO_BUFFER, outgoing_tok);
}

char *client_principal(void) {
    return complete ? (char *)peer_principal.value : NULL;
}

char *client_username(void) {
    if (!peer_username) {
        char *princ = client_principal();
        if (princ) {
            peer_username = xstrdup(princ);
            char *c = strchr(peer_username, '@');
            if (c)
                *c = '\0';
        }
    }
    return peer_username;
}

