#include <unistd.h>
#include <sys/types.h>
#include <pwd.h>
#include <grp.h>

#include "common.h"
#include "util.h"
#include "config.h"

int ceo_get_privileged() {
    int uid = getuid();

    // root is privileged
    if (!uid)
        return 1;

    if (privileged_group) {
        struct group *privgrp = getgrnam(privileged_group);
        int pgid;
        gid_t grps[128];
        int count, i;
        if (!privgrp)
            return 0;
        pgid = privgrp->gr_gid;

        count = getgroups(sizeof(grps)/sizeof(*grps), grps);
        for (i = 0; i < count; i++)
            if (grps[i] == pgid)
                return 1;
    }

    return 0;
}

char *ceo_get_user() {
    struct passwd *pwent = getpwuid(getuid());
    if (pwent == NULL)
        fatal("could not determine user");
    return xstrdup(pwent->pw_name);
}

void ceo_notify_hook(int argc, ...) {
    va_list args;
    char **argv;
    int i = 0;

    va_start(args, argc);

    argv = (char **)xmalloc(sizeof(char *) * (argc + 1));

    while (i < argc)
        argv[i++] = va_arg(args, char *);

    argv[i++] = NULL;
    spawnv(notify_hook, argv);

    va_end(args);
}
