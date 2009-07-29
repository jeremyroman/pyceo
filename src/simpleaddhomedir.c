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
    if(argc < 6) {
        fprintf(stderr, "Usage: simpleaddhomedir homedir skeldir uid gid mode\n");
        return 1;
    }

    char *homedir = argv[1];
    char *skeldir = argv[2];
    char *mode = argv[5];
    uid_t uid, gid;
    char *mkdir_bin = "/bin/mkdir";
    char *chmod_bin = "/bin/chmod";
    char *dataset = homedir;
    char *create_argv[] = { "mkdir", dataset, NULL };
    char *mode_argv[] = { "chmod", mode, homedir, NULL };
    DIR *skel;
    struct dirent *skelent;

    assert(homedir[0]);
    uid = atol(argv[3]);
    gid = atol(argv[4]);

    if(spawnv(mkdir_bin, create_argv))
        return 1;
    //Quotas are ignored now, or so I'm told.
    /* if(spawnv(zfs_bin, quota_argv)) */
    /*     return 1; */
    if(spawnv(chmod_bin, mode_argv))
        return 1;
    //Fuck ACLs.  The instructions I got didn't include them.
    /* if(acl && spawnv(chmod_bin, acl_argv)) */
    /*     return 1; */

    skel = opendir(skeldir);
    if (!skel) {
        errorpe("failed to open %s", skeldir);
        return -1;
    }

    while ((skelent = readdir(skel))) {
        struct stat sb;
        char src[PATH_MAX], dest[PATH_MAX];

        if (!strcmp(skelent->d_name, ".") || !strcmp(skelent->d_name, ".."))
            continue;

        snprintf(src, sizeof(src), "%s/%s", skeldir, skelent->d_name);
        snprintf(dest, sizeof(dest), "/%s/%s", homedir, skelent->d_name);
        lstat(src, &sb);

        if (sb.st_uid || sb.st_gid) {
            warn("not creating %s due to ownership", dest);
            continue;
        }

        if (S_ISREG(sb.st_mode)) {
            int bytes;
            char buf[4096];

            int srcfd = open(src, O_RDONLY);
            if (srcfd == -1) {
                warnpe("open: %s", src);
                continue;
            }

            int destfd = open(dest, O_WRONLY|O_CREAT|O_EXCL, sb.st_mode & 0777);
            if (destfd == -1) {
                warnpe("open: %s", dest);
                close(srcfd);
                continue;
            }

            for (;;) {
                bytes = read(srcfd, buf, sizeof(buf));
                if (!bytes)
                    break;
                if (bytes < 0) {
                    warnpe("read");
                    break;
                }
                if (write(destfd, buf, bytes) < 0) {
                    warnpe("write");
                    break;
                }
            }
            if (fchown(destfd, uid, gid))
                errorpe("chown: %s", dest);

            close(srcfd);
            close(destfd);
        } else if (S_ISDIR(sb.st_mode)) {
            if (mkdir(dest, sb.st_mode & 0777)) {
                warnpe("mkdir: %s", dest);
                continue;
            }
            if (chown(dest, uid, gid))
                errorpe("chown: %s", dest);
        } else if (S_ISLNK(sb.st_mode)) {
            char lnkdest[PATH_MAX];
            int bytes;
            bytes = readlink(src, lnkdest, sizeof(lnkdest));
            lnkdest[bytes] = '\0';
            if (bytes == -1) {
                warnpe("readlink: %s", src);
                continue;
            }
            if (symlink(lnkdest, dest)) {
                warnpe("symlink: %s", dest);
                continue;
            }
            if (lchown(dest, uid, gid))
                errorpe("lchown: %s", dest);
        } else {
            warn("not creating %s", dest);
        }
    }

    closedir(skel);

    if (chown(homedir, uid, gid)) {
        errorpe("failed to chown %s", homedir);
        return -1;
    }

    return 0;
}
