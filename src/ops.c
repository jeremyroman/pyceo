#include <errno.h>
#include <inttypes.h>
#include <unistd.h>
#include <fcntl.h>
#include <netdb.h>

#include "strbuf.h"
#include "ops.h"
#include "net.h"
#include "util.h"
#include "config.h"

static struct op *ops;

static const char *default_op_dir = "/usr/lib/ceod";
static const char *op_dir;

static void add_op(char *host, char *name, uint32_t id) {
    struct op *new = xmalloc(sizeof(struct op));
    errno = 0;
    new->next = ops;
    new->name = xstrdup(name);
    new->id = id;
    new->path = NULL;

    struct hostent *hostent = gethostbyname(host);
    if (!hostent)
        badconf("cannot add op %s: %s: %s", name, host, hstrerror(h_errno));
    new->hostname = strdup(hostent->h_name);
    new->local = !strcmp(fqdn.buf, hostent->h_name);
    new->addr = *(struct in_addr *)hostent->h_addr_list[0];

    if (new->local) {
        new->path = xmalloc(strlen(op_dir) + strlen("/op-") + strlen(name) + 1);
        sprintf(new->path, "%s/op-%s", op_dir, name);
        if (access(new->path, X_OK))
            fatalpe("cannot add op: %s: %s", name, new->path);
    }

    ops = new;
    debug("added op %s (%s%s)", new->name, new->local ? "" : "on ",
            new->local ? "local" : host);
}

struct op *get_local_op(uint32_t id) {
    for (struct op *op = ops; op; op = op->next) {
        if (op->local && op->id == id)
            return op;
    }
    return NULL;
}

struct op *find_op(const char *name) {
    for (struct op *op = ops; op; op = op->next) {
        if (!strcmp(name, op->name))
            return op;
    }
    return NULL;
}

void setup_ops(void) {
    char op_config_dir[1024];
    DIR *dp;
    struct dirent *de;
    struct strbuf line = STRBUF_INIT;
    unsigned lineno = 0;
    unsigned op_count = 0;

    op_dir = getenv("CEO_LIB_DIR") ?: default_op_dir;

    if (snprintf(op_config_dir, sizeof(op_config_dir), "%s/%s", config_dir, "ops.d") >= sizeof(op_config_dir))
        fatal("ops dir path too long");

    dp = opendir(op_config_dir);
    if (!dp)
        fatalpe("opendir: %s", op_config_dir);

    while ((de = readdir(dp))) {
        FILE *fp = fopenat(dp, de->d_name, O_RDONLY);
        if (!fp)
            warnpe("open: %s/%s", op_config_dir, de->d_name);
        while (strbuf_getline(&line, fp, '\n') != EOF) {
            lineno++;
            strbuf_trim(&line);

            if (!line.len || line.buf[0] == '#')
                continue;

            struct strbuf **words = strbuf_splitws(&line);

            if (strbuf_list_len(words) != 3)
                badconf("%s/%s: expected three words on line %d", op_config_dir, de->d_name, lineno);

            errno = 0;
            char *end;
            int id = strtol(words[2]->buf, &end, 0);
            if (errno || *end)
                badconf("%s/%s: invalid id '%s' on line %d", op_config_dir, de->d_name, words[2]->buf, lineno);

            add_op(words[0]->buf, words[1]->buf, id);
            op_count++;

            strbuf_list_free(words);
        }
        fclose(fp);
    }

    closedir(dp);
    strbuf_release(&line);
}

void free_ops(void) {
    while (ops) {
        struct op *next = ops->next;
        free(ops->name);
        free(ops->hostname);
        free(ops->path);
        free(ops);
        ops = next;
    }
}
