#include <unistd.h>
#include <sys/types.h>
#include <sys/wait.h>
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

static int use_stdin = 0;

static char *name = NULL;
static char *userid = NULL;
static char *program = NULL;
static char password[1024];

static struct option opts[] = {
    { "force", 0, NULL, 'f' },
    { "no-notify", 0, NULL, 'q' },
    { "stdin", 0, NULL, 's' },
    { NULL, 0, NULL, '\0' },
};

static void usage() {
    fprintf(stderr, "Usage: %s userid realname [program]\n", prog);
    exit(2);
}

int addmember() {
    int krb_ok, user_ok, group_ok, home_ok;
    int id;
    char homedir[1024];
    char acl_s[1024] = {0};

    logmsg("adding uid=%s cn=%s program=%s by %s", userid, name, program, user);

    if (setreuid(0, 0))
        fatalpe("setreuid");

    if (!force && getpwnam(userid) != NULL)
        deny("user %s already exists", userid);

    snprintf(homedir, sizeof(homedir), "%s/%s", member_home, userid);

    if (ceo_read_password(password, sizeof(password), use_stdin))
        return 1;

    ceo_krb5_init();
    ceo_ldap_init();
    ceo_kadm_init();

    if (ceo_user_exists(userid))
        deny("user %s already exists in LDAP", userid);

    if ((id = ceo_new_uid(member_min_id, member_max_id)) <= 0)
        fatal("no available uids in range [%d, %d]", member_min_id, member_max_id);

    if (*member_home_acl) {
        snprintf(acl_s, sizeof(acl_s), member_home_acl, userid);
    }

    krb_ok = ceo_del_princ(userid);
    krb_ok = krb_ok || ceo_add_princ(userid, password);
    if (!krb_ok)
        logmsg("successfully created principal for %s", userid);

    user_ok = krb_ok || ceo_add_user(userid, users_base, "member", name, homedir,
            member_shell, id, "program", program, NULL);
    if (!user_ok)
        logmsg("successfully created account for %s", userid);

    group_ok = user_ok || ceo_add_group(userid, groups_base, id);
    if (!group_ok)
        logmsg("successfully created group for %s", userid);

    home_ok = user_ok || ceo_create_home(homedir, id, id, homedir_mode, acl_s);
    if (!home_ok)
        logmsg("successfully created home directory for %s", userid);

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
            exit(execl(notify_hook, notify_hook, prog, user, userid, name, program, NULL));
        }

        hkf = fdopen(hkp[1], "w");

        if (group_ok)
            fprintf(hkf, "failed to create group\n");
        if (home_ok)
            fprintf(hkf, "failed to create home directory\n");
        if (!group_ok && !home_ok)
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

    return krb_ok || user_ok || group_ok || home_ok;
}

int main(int argc, char *argv[]) {
    int opt;

    prog = basename(argv[0]);
    openlog(prog, 0, LOG_AUTHPRIV);

    configure();

    user = ceo_get_user();
    privileged = ceo_get_privileged();

    while ((opt = getopt_long(argc, argv, "", opts, NULL)) != -1) {
        switch (opt) {
            case 's':
                use_stdin = 1;
                break;
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

    if (argc - optind != 2 && argc - optind != 3)
        usage();

    userid = argv[optind++];
    name = argv[optind++];

    if (argc - optind)
        program = argv[optind++];

    return addmember();
}
