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

    retval = kadm5_init_with_skey(
#ifdef KADM5_API_VERSION_3
        context,
#endif
        krb5_admin_principal, NULL,
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

    debug("kadmin: adding principal %s", user);

    // Added March 2012: Change behavior of ceod to add the kerberos principal.
    kadm5_policy_ent_rec defpol;
    kadm5_principal_ent_rec princ;

    memset((void*) &princ, 0, sizeof(princ));

    if ((retval = kadm5_get_policy(handle, "default", &defpol))) {
        com_err(prog, retval, "while retrieving default policy");
        return retval;
    }
    kadm5_free_policy_ent(handle, &defpol);

    princ.policy = "default";

    if ((retval = krb5_parse_name(context, user, &princ.principal))) {
        com_err(prog, retval, "while parsing user name");
        return retval;
    }

    long flags = KADM5_POLICY | KADM5_PRINCIPAL;
    if ((retval = kadm5_create_principal(handle, &princ, flags, password))) {
        if(retval == KADM5_DUP) {
            if ((retval = kadm5_chpass_principal(handle, princ.principal, password))) {
                com_err(prog, retval, "while setting principal password");
                return retval;
            }
        } else {
            com_err(prog, retval, "while creating principal");
            return retval;
        }
    }

    krb5_free_principal(context, princ.principal);
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
