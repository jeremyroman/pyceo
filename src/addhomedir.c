#include <stdio.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/acl.h>
#include <dirent.h>
#include <pwd.h>
#include <fcntl.h>

#include "addhomedir.h"
#include "util.h"
#include "config.h"

int ceo_create_home(char *homedir, uid_t uid, gid_t gid, acl_t acl, acl_t dacl) {
    int mask;
    DIR *skel;
    struct dirent *skelent;

    mask = umask(0);

    if (mkdir(homedir, 0755)) {
        errorpe("failed to create %s", homedir);
        return -1;
    }

    skel = opendir(skeleton_dir);
    if (!skel) {
        errorpe("failed to open %s", skeleton_dir);
        return -1;
    }

    while ((skelent = readdir(skel))) {
        struct stat sb;
        char src[PATH_MAX], dest[PATH_MAX];

        if (!strcmp(skelent->d_name, ".") || !strcmp(skelent->d_name, ".."))
            continue;

        snprintf(src, sizeof(src), "%s/%s", skeleton_dir, skelent->d_name);
        snprintf(dest, sizeof(dest), "%s/%s", homedir, skelent->d_name);
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

    if (acl && acl_set_file(homedir, ACL_TYPE_ACCESS, acl)) {
        errorpe("failed to set acl for %s", homedir);
        return -1;
    }

    if (dacl && acl_set_file(homedir, ACL_TYPE_DEFAULT, dacl)) {
        errorpe("failed to set default acl for %s", homedir);
        return -1;
    }

    umask(mask);

    return 0;
}

int ceo_set_quota(char *proto, int id) {
    char user[128];
    char *sqargs[] = { "setquota", "-a", "-p", proto, NULL, NULL };

    snprintf(user, sizeof(user), "%d", id);
    sqargs[4] = user;

    if (spawnv("/usr/sbin/setquota", sqargs)) {
        error("failed to set quota for %s", user);
        return -1;
    }

    return 0;
}
