#include <stdio.h>

#include <krb5.h>
#include <syslog.h>

#include "krb5.h"
#include "util.h"
#include "config.h"

extern char *prog;

krb5_context context;

static void com_err_hk(const char *whoami, long code, const char *fmt, va_list args) {
    char message[4096];
    char *msgp = message;

    msgp += snprintf(msgp, sizeof(message) - 2 - (msgp - message), "%s ", error_message(code));
    if (msgp - message > sizeof(message) - 2)
        fatal("error message overflowed");

    msgp += vsnprintf(msgp, sizeof(message) - 2 - (msgp - message), fmt, args);
    if (msgp - message > sizeof(message) - 2)
        fatal("error message overflowed");

    *msgp++ = '\n';
    *msgp++ = '\0';

    logmsg(LOG_ERR, "fatal: %s", message);
    exit(1);
}

void ceo_krb5_init() {
    krb5_error_code retval;

    set_com_err_hook(com_err_hk);

    debug("krb5: initializing context");

    retval = krb5_init_context(&context);
    if (retval)
        com_err(prog, retval, "while initializing krb5");

    retval = krb5_set_default_realm(context, krb5_realm);
    if (retval)
        com_err(prog, retval, "while setting default realm");
}

void ceo_krb5_auth(char *principal) {
    krb5_error_code retval;
    krb5_creds creds;
    krb5_principal princ;
    krb5_ccache cache;
    krb5_get_init_creds_opt options;

    krb5_get_init_creds_opt_init(&options);
    memset(&creds, 0, sizeof(creds));

    debug("krb5: getting TGT using keytab for %s", principal);

    if ((retval = krb5_parse_name(context, principal, &princ)))
        com_err(prog, retval, "while resolving user %s", principal);

    if ((retval = krb5_cc_default(context, &cache)))
        com_err(prog, retval, "while resolving credentials cache");

    if ((retval = krb5_get_init_creds_keytab(context, &creds, princ, NULL, 0, NULL, &options)))
        com_err(prog, retval, "while getting initial credentials");

    if ((retval = krb5_cc_initialize(context, cache, princ)))
        com_err(prog, retval, "while initializing credentials cache");

    if ((retval = krb5_cc_store_cred(context, cache, &creds)))
        com_err(prog, retval, "while storing credentials");

    krb5_free_cred_contents(context, &creds);
    krb5_free_principal(context, princ);
    krb5_cc_close(context, cache);
}

void ceo_krb5_deauth() {
    krb5_error_code retval;
    krb5_ccache cache;

    debug("krb5: destroying credentials");

    if ((retval = krb5_cc_default(context, &cache)))
        com_err(prog, retval, "while resolving credentials cache");

    if ((retval = krb5_cc_destroy(context, cache)))
        com_err(prog, retval, "while destroying credentials cache");
}

void ceo_krb5_cleanup() {
    debug("krb5: cleaning up");
    krb5_free_context(context);
}

int ceo_read_password(char *password, unsigned int size, int use_stdin) {
    int tries = 0;
    unsigned int len;

    do {
        if (use_stdin) {
            if (fgets(password, size, stdin) == NULL)
                fatal("eof while reading password");

            size = strlen(password);

            if (password[size - 1] == '\n')
                password[size - 1] = '\0';
        } else {
            len = size;
            int retval = krb5_read_password(context, "New password", "Confirm password", password, &len);
            if (retval == KRB5_LIBOS_PWDINTR) {
                error("interrupted");
                return -1;
            } else if (retval == KRB5_LIBOS_BADPWDMATCH) {
                fputs("Passwords do not match.\n", stderr);
            } else if (!password || !*password) {
                fputs("Please enter a password.\n", stderr);
            }
        }
    } while (++tries < 3 && !*password);

    if (!*password) {
        error("maximum tries exceeded reading password");
        return -1;
    }

    return 0;
}
