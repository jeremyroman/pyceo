#include <stdio.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/acl.h>
#include <dirent.h>
#include <pwd.h>
#include <fcntl.h>
#include <assert.h>

#include "addhomedir.h"
#include "util.h"
#include "config.h"
#include "krb5.h"

int ceo_create_home(char *homedir, uid_t uid, gid_t gid, char *mode, char *acl) {
    char uid_str[16], gid_str[16];
    char *zfs_argv[] = { "ssh", "ceo@ginseng", "/usr/sbin/zfsaddhomedir", \
        homedir, skeleton_dir, uid_str, gid_str, mode, acl, NULL };

    assert(homedir[0]);
    snprintf(uid_str, sizeof(uid_str), "%ld", (long)uid);
    snprintf(gid_str, sizeof(gid_str), "%ld", (long)uid);
    if(!acl[0]) acl = NULL;

    ceo_krb5_auth(admin_bind_userid, admin_bind_keytab);

    if(spawnv("/usr/bin/ssh", zfs_argv)) {
        errorpe("failed calling zfsaddhomedir for %s", homedir);
        return -1;
    }

    ceo_krb5_deauth();

    return 0;
}
