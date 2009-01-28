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

struct config_var {
    const char *name;
    void *p;
    enum { CONFIG_TYPE_STR, CONFIG_TYPE_INT } type;
};

#define CONFIG_STR(x) {#x, &x, CONFIG_TYPE_STR },
#define CONFIG_INT(x) {#x, &x, CONFIG_TYPE_INT },
static struct config_var config_vars[] = {
#include "config-vars.h"
};
#undef CONFIG_STR
#undef CONFIG_INT

void config_var(char *var, char *val) {
    int i;

    for (i = 0; i < sizeof(config_vars)/sizeof(*config_vars); i++) {
        if (!strcmp(var, config_vars[i].name)) {
            switch (config_vars[i].type) {
                case CONFIG_TYPE_STR:
                    if (*(char **)config_vars[i].p)
                        free(*(char **)config_vars[i].p);
                    *(char **)config_vars[i].p = xstrdup(val);
                    break;
                case CONFIG_TYPE_INT:
                    *(long *)config_vars[i].p = config_long(var, val);
                    break;
                default:
                    fatal("unknown config var type %d", config_vars[i].type);
            }
        }
    }
}

void configure() {
    int i;

    config_parse(CONFIG_FILE);

    for (i = 0; i < sizeof(config_vars)/sizeof(*config_vars); i++) {
        switch (config_vars[i].type) {
            case CONFIG_TYPE_STR:
                if (*(char **)config_vars[i].p == DEF_STR)
                    badconf("undefined string variable: %s", config_vars[i].name);
                break;
            case CONFIG_TYPE_INT:
                if (*(long *)config_vars[i].p == DEF_INT)
                    badconf("undefined integer variable: %s", config_vars[i].name);
                break;
            default:
                fatal("unknown config var type %d", config_vars[i].type);
        }
    }
}
