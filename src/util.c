#include <unistd.h>
#include <sys/wait.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdarg.h>
#include <syslog.h>
#include <errno.h>

#include "util.h"

static char message[4096];

static int log_stderr = 1;

void init_log(const char *ident, int option, int facility) {
    openlog(ident, option, facility);
    log_stderr = isatty(STDERR_FILENO);
}

static void errmsg(int prio, const char *prefix, const char *fmt, va_list args) {
    char *msgp = message;

    msgp +=  snprintf(msgp, sizeof(message) - 2 - (msgp - message), "%s: ", prefix);
    if (msgp - message > sizeof(message) - 2)
        fatal("error message overflowed");

    msgp += vsnprintf(msgp, sizeof(message) - 2 - (msgp - message), fmt, args);
    if (msgp - message > sizeof(message) - 2)
        fatal("error message overflowed");

    *msgp++ = '\n';
    *msgp++ = '\0';

    syslog(prio, "%s", message);
    if (log_stderr)
        fputs(message, stderr);
}

static void errmsgpe(int prio, const char *prefix, const char *fmt, va_list args) {
    char *msgp = message;

    msgp += snprintf(msgp, sizeof(message) - 2 - (msgp - message), "%s: ", prefix);
    if (msgp - message > sizeof(message) - 2)
        fatal("error message overflowed");

    msgp += vsnprintf(msgp, sizeof(message) - 2 - (msgp - message), fmt, args);
    if (msgp - message > sizeof(message) - 2)
        fatal("error message overflowed");

    msgp += snprintf(msgp, sizeof(message) - 2 - (msgp - message), ": %s", strerror(errno));
    if (msgp - message > sizeof(message) - 2)
        fatal("error message overflowed");

    *msgp++ = '\n';
    *msgp++ = '\0';

    syslog(prio, "%s", message);
    if (log_stderr)
        fputs(message, stderr);
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

int spawnv(const char *path, char *argv[]) {
    int pid, status;
    pid = fork();
    if (pid == -1)
        fatalpe("fork");
    else if (pid)
        waitpid(pid, &status, 0);
    else
        exit(execv(path, argv));
    return status;
}
