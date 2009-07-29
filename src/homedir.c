#include <stdio.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <sys/acl.h>
#include <dirent.h>
#include <pwd.h>
#include <fcntl.h>

#include "homedir.h"
#include "util.h"
#include "config.h"

int ceo_create_home(char *homedir, char *skel, uid_t uid, gid_t gid) {
    int mask;
    DIR *skeldir;
    struct dirent *skelent;

    mask = umask(0);

    if (mkdir(homedir, 0755)) {
        errorpe("failed to create %s", homedir);
        return -1;
    }

    skeldir = opendir(skel);
    if (!skeldir) {
        errorpe("failed to open %s", skel);
        return -1;
    }

    while ((skelent = readdir(skeldir))) {
        struct stat sb;
        char src[PATH_MAX], dest[PATH_MAX];

        if (!strcmp(skelent->d_name, ".") || !strcmp(skelent->d_name, ".."))
            continue;

        snprintf(src, sizeof(src), "%s/%s", skel, skelent->d_name);
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

    closedir(skeldir);

    if (chown(homedir, uid, gid)) {
        errorpe("failed to chown %s", homedir);
        return -1;
    }

    umask(mask);

    return 0;
}
