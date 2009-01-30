#include <stdio.h>
#include <unistd.h>
#include <dirent.h>
#include <limits.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <fcntl.h>
#include <assert.h>
#include "util.h"

int main(int argc, char *argv[]) {
    if(argc < 7) {
        fprintf(stderr, "Usage: zfsaddhomedir homedir refquota skeldir uid gid mode acl\n");
        return 1;
    }

    {
        char *homedir = argv[1];
        char *skeldir = argv[3];
        char refquota[32];
        char *mode = argv[6];
        char *acl = (argc >= 8) ? argv[7] : NULL;
        uid_t uid, gid;
        char *zfs_bin = "/usr/sbin/zfs";
        char *chmod_bin = "/usr/bin/chmod";
        char *rsync_bin = "/usr/bin/rsync";
        char *dataset = homedir + 1;
        char *create_argv[] = { "zfs", "create", dataset, NULL };
        char *quota_argv[] = { "zfs", "set", refquota, dataset, NULL };
        char *mode_argv[] = { "chmod", mode, homedir, NULL };
        char *acl_argv[] = { "chmod", acl, homedir, NULL };
        char *rsync_argv[] = { "rsync", "-avH", skeldir, homedir, NULL };
        DIR *skel;
        struct dirent *skelent;

        assert(homedir[0]);
        uid = atol(argv[4]);
        gid = atol(argv[5]);
        snprintf(refquota, sizeof(refquota), "refquota=%s", argv[2]);

        if(spawnv(zfs_bin, create_argv))
            return 1;
        if(spawnv(zfs_bin, quota_argv))
            return 1;
        if(spawnv(chmod_bin, mode_argv))
            return 1;
        if(acl && spawnv(chmod_bin, acl_argv))
            return 1;

        if (chown(homedir, uid, gid)) {
            errorpe("failed to chown %s", homedir);
            return -1;
        }

        if(seteuid(uid) != 0 || setegid(gid) != 0)
            return 1;
        if(spawnv(rsync_bin, rsync_argv))
            return 1;
    }

    return 0;
}
