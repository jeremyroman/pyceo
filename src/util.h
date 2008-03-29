#ifndef CEO_UTIL_H
#define CEO_UTIL_H

#include <stdlib.h>
#include <string.h>
#include <stdarg.h>

#ifdef __GNUC__
#define NORETURN __attribute__((__noreturn__))
#else
#define NORETURN
#endif

#ifndef LOG_AUTHPRIV
#define LOG_AUTHPRIV LOG_AUTH
#endif

int spawnv(const char *, char *[]);

NORETURN void fatal(const char *, ...);
NORETURN void fatalpe(const char *, ...);
NORETURN void badconf(const char *, ...);
NORETURN void deny(const char *, ...);
void error(const char *, ...);
void warn(const char *, ...);
void logmsg(const char *, ...);
void errorpe(const char *, ...);
void warnpe(const char *, ...);

static inline void *xmalloc(size_t size) {
    void *alloc = malloc(size);

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
