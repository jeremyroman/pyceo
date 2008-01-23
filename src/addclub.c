#include <unistd.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <sys/acl.h>
#include <stdio.h>
#include <stdlib.h>
#include <getopt.h>
#include <ctype.h>
#include <pwd.h>
#include <grp.h>
#include <errno.h>
#include <libgen.h>
#include <syslog.h>

#include "util.h"
#include "common.h"
#include "config.h"
#include "ldap.h"
#include "krb5.h"
#include "kadm.h"
#include "addhomedir.h"

char *prog = NULL;
char *user = NULL;
int privileged = 0;

static int force = 0;
static int no_notify = 0;

static char *name = NULL;
static char *userid = NULL;

static struct option opts[] = {
    { "force", 0, NULL, 'f' },
    { "no-notify", 0, NULL, 'q' },
    { NULL, 0, NULL, '\0' },
};

static void usage() {
    fprintf(stderr, "Usage: %s userid clubname\n", prog);
    exit(2);
}

int addclub() {
    int krb_ok, user_ok, group_ok, sudo_ok, home_ok, quota_ok;
    int id;
    char homedir[1024];
    char acl_s[1024], dacl_s[1024];
    acl_t acl = NULL, dacl = NULL;

    logmsg("adding uid=%s cn=%s by %s", userid, name, user);

    if (setreuid(0, 0))
        fatalpe("setreuid");

    if (!force && getpwnam(userid) != NULL)
        deny("user %s already exists", userid);

    snprintf(homedir, sizeof(homedir), "%s/%s", club_home, userid);
    ceo_krb5_init();
    ceo_ldap_init();
    ceo_kadm_init();

    if (ceo_user_exists(userid))
        deny("user %s already exists in LDAP", userid);

    if ((id = ceo_new_uid(member_min_id, member_max_id)) <= 0)
        fatal("no available uids in range [%d, %d]", member_min_id, member_max_id);

    snprintf(acl_s, sizeof(acl_s), club_home_acl, id);

    acl = acl_from_text(acl_s);
    if (acl == NULL)
        fatalpe("Unable to parse club_home_acl");

    if (*club_home_dacl) {
        snprintf(dacl_s, sizeof(dacl_s), club_home_dacl, id);
        dacl = acl_from_text(dacl_s);
        if (dacl == NULL)
            fatalpe("Unable to parse club_home_dacl");
    }


    krb_ok = ceo_del_princ(userid);
    if (!krb_ok)
        logmsg("successfully cleared principal for %s", userid);

    user_ok = krb_ok || ceo_add_user(userid, users_base, "club", name, homedir,
            club_shell, id, NULL);
    if (!user_ok)
        logmsg("successfully created account for %s", userid);

    group_ok = user_ok || ceo_add_group(userid, groups_base, id);
    if (!group_ok)
        logmsg("successfully created group for %s", userid);

    sudo_ok = user_ok || ceo_add_group_sudo(userid, sudo_base);
    if (!sudo_ok)
        logmsg("successfully added group sudo entry for %s", userid);

    home_ok = user_ok || ceo_create_home(homedir, id, id, acl, dacl);
    if (!home_ok)
        logmsg("successfully created home directory for %s", userid);

    quota_ok = user_ok || ceo_set_quota(quota_prototype, id);
    if (!quota_ok)
        logmsg("successfully set quota for %s", userid);

    logmsg("done uid=%s", userid);

    if (!no_notify && !user_ok) {
        int pid;
        int hkp[2];
        FILE *hkf;
        int status;

        if (pipe(hkp))
            errorpe("pipe");

        fflush(stdout);
        fflush(stderr);

        pid = fork();

        if (!pid) {
            fclose(stdout);
            fclose(stderr);
            close(hkp[1]);
            dup2(hkp[0], 0);
            exit(execl(notify_hook, notify_hook, prog, user, userid, name, NULL));
        }

        hkf = fdopen(hkp[1], "w");

        if (group_ok)
            fprintf(hkf, "failed to create group\n");
        if (home_ok)
            fprintf(hkf, "failed to create home directory\n");
        if (quota_ok)
            fprintf(hkf, "failed to set quota\n");
        if (!group_ok && !home_ok && !quota_ok)
            fprintf(hkf, "all failures went undetected\n");

        fclose(hkf);

        waitpid(pid, &status, 0);

        if (WIFEXITED(status) && WEXITSTATUS(status))
            logmsg("hook %s exited with status %d", notify_hook, WEXITSTATUS(status));
        else if (WIFSIGNALED(status))
            logmsg("hook %s killed by signal %d", notify_hook, WTERMSIG(status));
    }

    ceo_kadm_cleanup();
    ceo_ldap_cleanup();
    ceo_krb5_cleanup();

    return krb_ok || user_ok || group_ok || home_ok || quota_ok;
}

int main(int argc, char *argv[]) {
    int opt;

    openlog(prog, 0, LOG_AUTHPRIV);

    configure();

    prog = basename(argv[0]);
    user = ceo_get_user();
    privileged = ceo_get_privileged();

    while ((opt = getopt_long(argc, argv, "", opts, NULL)) != -1) {
        switch (opt) {
            case 'f':
                if (!privileged)
                    deny("not privileged enough to force");
                force = 1;
                break;
            case 'q':
                if (!privileged)
                    deny("not privileged enough to suppress notifications");
                no_notify = 1;
                break;
            case '?':
                usage();
                break;
            default:
                fatal("error parsing arguments");
        }
    }

    if (argc - optind != 2)
        usage();

    userid = argv[optind++];
    name = argv[optind++];

    return addclub();
}
