#define _ATFILE_SOURCE
#include <unistd.h>
#include <sys/wait.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <fcntl.h>
#include <syslog.h>
#include <errno.h>
#include <grp.h>

#include "util.h"
#include "strbuf.h"

static int log_stderr = 1;

void init_log(const char *ident, int option, int facility) {
    openlog(ident, option, facility);
    log_stderr = isatty(STDERR_FILENO);
}

static void errmsg(int prio, const char *prefix, const char *fmt, va_list args) {
    struct strbuf msg = STRBUF_INIT;

    strbuf_addf(&msg, "%s: ", prefix);
    strbuf_vaddf(&msg, fmt, args);
    strbuf_addch(&msg, '\n');

    syslog(prio, "%s", msg.buf);
    if (log_stderr)
        fputs(msg.buf, stderr);
}

static void errmsgpe(int prio, const char *prefix, const char *fmt, va_list args) {
    struct strbuf msg = STRBUF_INIT;

    strbuf_addf(&msg, "%s: ", prefix);
    strbuf_vaddf(&msg, fmt, args);
    strbuf_addf(&msg, ": %s\n", strerror(errno));

    syslog(prio, "%s", msg.buf);
    if (log_stderr)
        fputs(msg.buf, stderr);
}

NORETURN static void die(int prio, const char *prefix, const char *msg, va_list args) {
    errmsg(prio, prefix, msg, args);
    exit(1);
}

NORETURN static void diepe(int prio, const char *prefix, const char *msg, va_list args) {
    errmsgpe(prio, prefix, msg, args);
    exit(1);
}

NORETURN void fatal(const char *msg, ...) {
    va_list args;
    va_start(args, msg);
    die(LOG_CRIT, "fatal", msg, args);
    va_end(args);
}

void error(const char *msg, ...) {
    va_list args;
    va_start(args, msg);
    errmsg(LOG_ERR, "error", msg, args);
    va_end(args);
}

void warn(const char *msg, ...) {
    va_list args;
    va_start(args, msg);
    errmsg(LOG_WARNING, "warning", msg, args);
    va_end(args);
}

void notice(const char *msg, ...) {
    va_list args;
    va_start(args, msg);
    errmsg(LOG_NOTICE, "notice", msg, args);
    va_end(args);
}

void debug(const char *msg, ...) {
    va_list args;
    va_start(args, msg);
    errmsg(LOG_DEBUG, "debug", msg, args);
    va_end(args);
}

void logmsg(int priority, const char *msg, ...) {
    va_list args;
    va_start(args, msg);
    vsyslog(priority, msg, args);
    va_end(args);
    va_start(args, msg);
    if (log_stderr) {
        vfprintf(stderr, msg, args);
        fputc('\n', stderr);
    }
    va_end(args);
}

NORETURN void deny(const char *msg, ...) {
    va_list args;
    va_start(args, msg);
    die(LOG_ERR, "denied", msg, args);
    va_end(args);
}

NORETURN void badconf(const char *msg, ...) {
    va_list args;
    va_start(args, msg);
    die(LOG_CRIT, "configuration error", msg, args);
    va_end(args);
}

NORETURN void fatalpe(const char *msg, ...) {
    va_list args;
    va_start(args, msg);
    diepe(LOG_CRIT, "fatal", msg, args);
    va_end(args);
}

void errorpe(const char *msg, ...) {
    va_list args;
    va_start(args, msg);
    errmsgpe(LOG_ERR, "error", msg, args);
    va_end(args);
}

void warnpe(const char *msg, ...) {
    va_list args;
    va_start(args, msg);
    errmsgpe(LOG_WARNING, "warning", msg, args);
    va_end(args);
}

int spawnv(const char *path, char *const argv[]) {
    int pid, status;

    fflush(stdout);
    fflush(stderr);

    pid = fork();
    if (pid < 0)
        fatalpe("fork");
    else if (pid)
        waitpid(pid, &status, 0);
    else
        exit(execv(path, argv));
    return status;
}

void full_write(int fd, const void *buf, size_t count) {
    ssize_t total = 0;

    while (total < count) {
        ssize_t wcount = write(fd, (char *)buf + total, count - total);
        if (wcount < 0)
            fatalpe("write");
        total += wcount;
    }
}

int spawnvem(const char *path, char *const *argv, char *const *envp, const struct strbuf *output, struct strbuf *input, int cap_stderr) {
    int pid, wpid, status;
    int tochild[2];
    int fmchild[2];

    if (pipe(tochild))
        fatalpe("pipe");
    if (pipe(fmchild))
        fatalpe("pipe");

    fflush(stdout);
    fflush(stderr);

    pid = fork();
    if (pid < 0)
        fatalpe("fork");
    if (!pid) {
        dup2(tochild[0], STDIN_FILENO);
        dup2(fmchild[1], STDOUT_FILENO);
        if (cap_stderr)
            dup2(STDOUT_FILENO, STDERR_FILENO);
        close(tochild[0]);
        close(tochild[1]);
        close(fmchild[0]);
        close(fmchild[1]);
        execve(path, argv, envp);
        fatalpe("execve");
    } else {
        close(tochild[0]);
        close(fmchild[1]);
        full_write(tochild[1], output->buf, output->len);
        close(tochild[1]);

        if (input)
            strbuf_read(input, fmchild[0], 0);
        close(fmchild[0]);
    }

    wpid = waitpid(pid, &status, 0);
    if (wpid < 0)
        fatalpe("waitpid");
    else if (wpid != pid)
        fatal("waitpid is broken");

    if (WIFEXITED(status) && WEXITSTATUS(status))
        notice("child %s exited with status %d", path, WEXITSTATUS(status));
    else if (WIFSIGNALED(status))
        notice("child %s killed by signal %d", path, WTERMSIG(status));

    return status;
}

int spawnv_msg(const char *path, char *const *argv, const struct strbuf *output) {
    return spawnvem(path, argv, environ, output, NULL, 0);
}

int check_group(char *username, char *group) {
    struct group *grp = getgrnam(group);
    char **members;

    if (grp)
        for (members = grp->gr_mem; *members; members++)
            if (!strcmp(username, *members))
                return 1;

    return 0;
}

FILE *fopenat(DIR *d, const char *path, int flags) {
    int dfd = dirfd(d);
    if (dfd < 0)
        return NULL;
    int fd = openat(dfd, path, flags);
    if (fd < 0)
        return NULL;
    return fdopen(fd, flags & O_RDWR   ? "r+" :
                      flags & O_WRONLY ? "w" :
                                         "r");
}

void make_env(char **envp, ...) {
    const size_t len = 4096;
    size_t used = 0;
    int args = 0;
    char *buf = xmalloc(len);
    va_list ap;
    va_start(ap, envp);
    char *name, *val;

    while ((name = va_arg(ap, char *))) {
        val = va_arg(ap, char *);
        if (!val)
            continue;
        int n = snprintf(buf + used, len - used, "%s=%s", name, val);
        if (n < 0)
            fatalpe("snprintf");
        if (n >= len - used)
            fatal("environment too big");

        envp[args++] = buf + used;
        used += n + 1;
    }

    if (!args)
        free(buf);

    envp[args] = NULL;
}

void free_env(char **envp) {
    free(*envp);
}
