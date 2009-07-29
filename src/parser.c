#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
#include <ctype.h>
#include <string.h>
#include <limits.h>

#include "parser.h"
#include "util.h"
#include "config.h"

#define VAR_MAX 256

void config_var(const char *, const char *);

struct config_file {
    FILE *p;
    char *name;
    int line;
    struct config_file *parent;
    int comment;
};

static void parse_config_file(char *, struct config_file *);
static void parse_error(struct config_file *file, char *msg) {
    fatal("parse error on line %d of %s: %s", file->line, file->name, msg);
}

static int parse_char(struct config_file *file) {
    int c = getc(file->p);
    if (c == '\n')
        (file->line)++;
    return c;
}

static void unparse_char(struct config_file *file, int c) {
    if (c == EOF)
        return;
    ungetc(c, file->p);
    if (c == '\n')
        (file->line)--;
}

static void parse_name(struct config_file *file, char *name, size_t maxlen) {
    int len = 0;
    int c;

    for (;;) {
        c = parse_char(file);

        if (c == EOF || c == '\n') {
            unparse_char(file, c);
            break;
        }

        if (!isalpha(c) && !isdigit(c) && c != '_' && c != '-') {
            unparse_char(file, c);
            break;
        }

        if (len == maxlen - 1)
            parse_error(file, "max name length exceeded");

        name[len++] = c;
    }

    if (len == 0)
        parse_error(file, "expected name");

    name[len++] = '\0';
}

static void parse_value(struct config_file *file, char *value, size_t maxlen) {
    int len = 0;
    int quote = 0;
    int comment = 0;
    int space = 0;
    int c;

    for (;;) {
        c = parse_char(file);

        if (c == EOF || c == '\n')
            break;

        if (c == '#')
            comment = 1;

        if ((isspace(c) && !quote) || comment) {
            space = 1;
            continue;
        }

        if (c == '"') {
            quote = ! quote;
            continue;
        }

        if (len == maxlen - space - 1)
            parse_error(file, "max value length exceeded");

        if (space && len) {
            value[len++] = ' ';
        }

        space = 0;
        value[len++] = c;
    }

    if (quote)
        parse_error(file, "unbalanced quotes");

    value[len++] = '\0';
}

static void parse_include(struct config_file *file) {
    char path[PATH_MAX];
    struct config_file *parent = file->parent;

    parse_value(file, path, sizeof(path));

    while (parent != NULL) {
        if (!strcmp(file->name, parent->name))
            return;
        parent = parent->parent;
    }

    parse_config_file(path, file);
}

static void parse_config(struct config_file *file) {
    int c;
    int comment = 0;

    char var[VAR_MAX];
    char value[VAR_MAX];

    for (;;) {
        c = parse_char(file);

        if (c == '\n') {
            comment = 0;
            continue;
        }

        if (c == EOF)
            return;

        if (isspace(c) | comment)
            continue;

        if (c == '#') {
            comment = 1;
            continue;
        }

        unparse_char(file, c);
        parse_name(file, var, sizeof(var));

        if (!strcmp(var, "include")) {
            parse_include(file);
            continue;
        }

        for (;;) {
            c = parse_char(file);
            if (c == EOF || c == '\n')
                parse_error(file, "expected '=' before line end");
            if (c == '=')
                break;
            if (!isspace(c))
                parse_error(file, "expected '='");
        }

        parse_value(file, value, sizeof(value));
        config_var(var, value);
    }
}

static void parse_config_file(char *name, struct config_file *parent) {
    struct config_file file;

    file.p = fopen(name, "r");
    file.name = name;
    file.line = 1;
    file.parent = parent;

    if (!file.p) {
        if (parent)
            parse_error(parent, strerror(errno));
        else
            fatal("failed to open configuration file '%s': %s", name, strerror(errno));
    }

    parse_config(&file);

    fclose(file.p);
}

long config_long(char *var, char *val) {
    char *endptr;
    long longval;

    longval = strtol(val, &endptr, 0);

    if (*val == '\0' || *endptr != '\0')
        fatal("expected integer value for %s", var);

    return longval;
}

void config_parse(char *filename) {
    debug("loading configuration from %s", filename);
    parse_config_file(filename, NULL);
}
