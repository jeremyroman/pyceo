#ifndef CEO_UTIL_H
#define CEO_UTIL_H

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <stdarg.h>
#include <syslog.h>
#include <sys/types.h>
#include <dirent.h>

#include "strbuf.h"

#ifdef __GNUC__
#define NORETURN __attribute__((__noreturn__))
#define PRINTF_LIKE(extra) __attribute__((format(printf, extra+1, extra+2)))
#else
#define NORETURN
#define PRINTF_LIKE(extra)
#endif

#ifndef LOG_AUTHPRIV
#define LOG_AUTHPRIV LOG_AUTH
#endif

extern char **environ;

int spawnv(const char *path, char *const *argv);
int spawnv_msg(const char *path, char *const *argv, const struct strbuf *output);
int spawnvem(const char *path, char *const *argv, char *const *envp, const struct strbuf *output, struct strbuf *input, int cap_stderr);
void full_write(int fd, const void *buf, size_t count);
ssize_t full_read(int fd, void *buf, size_t len);
FILE *fopenat(DIR *d, const char *path, int flags);
void make_env(char **envp, ...);
void free_env(char **envp);
void init_log(const char *ident, int option, int facility, int lstderr);
int check_group(char *username, char *group);
void log_set_maxprio(int prio);

PRINTF_LIKE(0) NORETURN void fatal(const char *, ...);
PRINTF_LIKE(0) NORETURN void fatalpe(const char *, ...);
PRINTF_LIKE(0) NORETURN void badconf(const char *, ...);
PRINTF_LIKE(0) NORETURN void deny(const char *, ...);
PRINTF_LIKE(0) void error(const char *, ...);
PRINTF_LIKE(0) void warn(const char *, ...);
PRINTF_LIKE(0) void notice(const char *, ...);
PRINTF_LIKE(0) void debug(const char *, ...);
PRINTF_LIKE(0) void errorpe(const char *, ...);
PRINTF_LIKE(0) void warnpe(const char *, ...);
PRINTF_LIKE(1) void logmsg(int priority, const char *, ...);

static inline void *xmalloc(size_t size) {
    void *alloc = malloc(size);

    if (alloc == NULL)
        fatal("out of memory");

    return alloc;
}

static inline void *xrealloc(void *ptr, size_t size) {
    void *alloc = realloc(ptr, size);

    if (alloc == NULL)
        fatal("out of memory");

    return alloc;
}

static inline void *xcalloc(size_t nmemb, size_t size) {
    void *alloc = calloc(nmemb, size);

    if (alloc == NULL)
        fatal("out of memory");

    return alloc;
}

static inline char *xstrdup(const char *s) {
    char *dup = strdup(s);

    if (dup == NULL)
        fatal("out of memory");

    return dup;
}

#endif
