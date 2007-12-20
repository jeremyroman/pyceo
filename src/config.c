#include <stdlib.h>
#include <limits.h>

#include "config.h"
#include "parser.h"
#include "util.h"

#define DEF_STR NULL
#define DEF_LONG LONG_MIN

char *server_url = DEF_STR;

char *users_base = DEF_STR;
char *groups_base = DEF_STR;
char *sudo_base = DEF_STR;

char *skeleton_dir = DEF_STR;
char *quota_prototype = DEF_STR;

char *member_home = DEF_STR;
char *member_shell = DEF_STR;
long member_min_id = DEF_LONG;
long member_max_id = DEF_LONG;

char *club_home = DEF_STR;
char *club_shell = DEF_STR;
long club_min_id = DEF_LONG;
long club_max_id = DEF_LONG;

char *notify_hook = DEF_STR;

long homedir_mode = DEF_LONG;

char *realm = DEF_STR;

char *admin_principal = DEF_STR;
char *admin_keytab = DEF_STR;

char *admin_bind_userid = DEF_STR;
char *admin_bind_keytab = DEF_STR;

char *sasl_realm = DEF_STR;
char *sasl_mech = DEF_STR;

char *privileged_group = DEF_STR;

static char *strvarnames[] = { "server_url", "users_base", "admin_principal",
    "admin_keytab", "skeleton_dir", "quota_prototype", "member_home",
    "member_shell", "club_home", "club_shell", "realm", "admin_bind_userid",
    "admin_bind_keytab", "groups_base", "privileged_group", "notify_hook",
    "sasl_realm", "sasl_mech", "sudo_base" };
static char **strvars[] = { &server_url, &users_base, &admin_principal,
    &admin_keytab, &skeleton_dir, &quota_prototype, &member_home,
    &member_shell, &club_home, &club_shell, &realm, &admin_bind_userid,
    &admin_bind_keytab, &groups_base, &privileged_group, &notify_hook,
    &sasl_realm, &sasl_mech, &sudo_base };

static char *longvarnames[] = { "member_min_id", "member_max_id",
    "homedir_mode", "club_min_id", "club_max_id" };
static long *longvars[] = { &member_min_id, &member_max_id, &homedir_mode,
    &club_min_id, &club_max_id };

void config_var(char *var, char *val) {
    int i;

    for (i = 0; i < sizeof(strvars)/sizeof(*strvars); i++) {
        if (!strcmp(var, strvarnames[i])) {
            if (!strvars[i])
                free(strvars[i]);
            *strvars[i] = xstrdup(val);
        }
    }

    for (i = 0; i < sizeof(longvars)/sizeof(*longvars); i++) {
        if (!strcmp(var, longvarnames[i])) {
            *longvars[i] = config_long(var, val);
        }
    }
}

void configure() {
    int i;

    config_parse(CONFIG_FILE);

    for (i = 0; i < sizeof(strvars)/sizeof(*strvars); i++) {
        if (*strvars[i] == DEF_STR)
            badconf("undefined string variable: %s", strvarnames[i]);
    }

    for (i = 0; i < sizeof(longvars)/sizeof(*longvars); i++) {
        if (*longvars[i] == DEF_LONG)
            badconf("undefined long variable: %s", longvarnames[i]);
    }
}
