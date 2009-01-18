#include <stdlib.h>
#include <limits.h>

#include "config.h"
#include "parser.h"
#include "util.h"

#define DEF_STR NULL
#define DEF_INT LONG_MIN

#define CONFIG_STR(x) char *x = DEF_STR;
#define CONFIG_INT(x) long  x = DEF_INT;
#include "config-vars.h"
#undef CONFIG_STR
#undef CONFIG_INT

struct config_var_str {
    const char *name;
    char **p;
};

struct config_var_int {
    const char *name;
    long *p;
};

#define CONFIG_STR(x) {#x, &x},
#define CONFIG_INT(x)
static struct config_var_str str_vars[] = {
#include "config-vars.h"
};
#undef CONFIG_STR
#undef CONFIG_INT

#define CONFIG_STR(x)
#define CONFIG_INT(x) {#x, &x},
static struct config_var_int int_vars[] = {
#include "config-vars.h"
};
#undef CONFIG_STR
#undef CONFIG_INT

void config_var(char *var, char *val) {
    int i;

    for (i = 0; i < sizeof(str_vars)/sizeof(*str_vars); i++) {
        if (!strcmp(var, str_vars[i].name)) {
            if (*str_vars[i].p)
                free(*str_vars[i].p);
            *str_vars[i].p = xstrdup(val);
        }
    }

    for (i = 0; i < sizeof(int_vars)/sizeof(*int_vars); i++) {
        if (!strcmp(var, int_vars[i].name)) {
            *int_vars[i].p = config_long(var, val);
        }
    }
}

void configure() {
    int i;

    config_parse(CONFIG_FILE);

    for (i = 0; i < sizeof(str_vars)/sizeof(*str_vars); i++) {
        if (*str_vars[i].p == DEF_STR)
            badconf("undefined string variable: %s", str_vars[i].name);
    }

    for (i = 0; i < sizeof(int_vars)/sizeof(*int_vars); i++) {
        if (*int_vars[i].p == DEF_INT)
            badconf("undefined integer variable: %s", int_vars[i].name);
    }
}
