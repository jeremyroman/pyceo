#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>

#include "parser.h"
#include "util.h"

void config_var(const char *name, const char *value) {
    printf("%s = \"%s\"\n", name, value);
}

int main(int argc, char *argv[]) {
    if (argc < 2) {
        fprintf(stderr, "usage: %s filename\n\n", argv[0]);
        exit(1);
    }

    config_parse(argv[1]);

    return 0;
}
