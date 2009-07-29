#include <kadm5/admin.h>

#include "kadm.h"
#include "krb5.h"
#include "util.h"
#include "config.h"

extern char *prog;

static void *handle;

void ceo_kadm_init() {
    krb5_error_code retval;
    kadm5_config_params params;
    memset((void *) &params, 0, sizeof(params));

    debug("kadmin: initializing using keytab for %s", krb5_admin_principal);

    retval = kadm5_init_with_skey(krb5_admin_principal, NULL,
                KADM5_ADMIN_SERVICE, &params, KADM5_STRUCT_VERSION,
                KADM5_API_VERSION_2, NULL, &handle);
    if (retval || !handle) {
        com_err(prog, retval, "while initializing kadm5");
        exit(1);
    }
}

void ceo_kadm_cleanup() {
    debug("kadmin: cleaning up");
    kadm5_destroy(handle);
}

int ceo_add_princ(char *user, char *password) {
    krb5_error_code retval;
    krb5_principal princ;
    memset((void *) &princ, 0, sizeof(princ));

    debug("kadmin: adding principal %s", user);

    if ((retval = krb5_parse_name(context, user, &princ))) {
        com_err(prog, retval, "while parsing principal name");
        return retval;
    }

    if ((retval = kadm5_chpass_principal(handle, princ, password))) {
        com_err(prog, retval, "while creating principal");
        return retval;
    }

    krb5_free_principal(context, princ);
    return 0;
}

int ceo_del_princ(char *user) {
    krb5_error_code retval;
    krb5_principal princ;

    debug("kadmin: deleting principal %s", user);

    if ((retval = krb5_parse_name(context, user, &princ))) {
        com_err(prog, retval, "while parsing principal name");
        return retval;
    }

    retval = kadm5_delete_principal(handle, princ);
    if (retval && retval != KADM5_UNK_PRINC) {
        com_err(prog, retval, "while deleting principal");
        return retval;
    }

    krb5_free_principal(context, princ);
    return 0;
}
