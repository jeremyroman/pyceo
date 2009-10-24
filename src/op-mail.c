#include <string.h>
#include <stdio.h>
#include <unistd.h>
#include <signal.h>
#include <syslog.h>
#include <libgen.h>
#include <getopt.h>
#include <errno.h>
#include <netdb.h>
#include <alloca.h>
#include <pwd.h>
#include <grp.h>
#include <fcntl.h>
#include <sys/wait.h>
#include <sys/stat.h>
#include <ctype.h>

#include "util.h"
#include "net.h"
#include "ceo.pb-c.h"
#include "config.h"
#include "strbuf.h"

char *prog;

static const int MAX_MESSAGES = 32;
static const int MAX_MESGSIZE = 512;

Ceo__UpdateMailResponse *response_create(void) {
    Ceo__UpdateMailResponse *r = xmalloc(sizeof(Ceo__UpdateMailResponse));
    ceo__update_mail_response__init(r);
    r->n_messages = 0;
    r->messages = xmalloc(MAX_MESSAGES *  sizeof(Ceo__StatusMessage *));
    return r;
}

PRINTF_LIKE(2)
int32_t response_message(Ceo__UpdateMailResponse *r, int32_t status, char *fmt, ...) {
    va_list args;
    Ceo__StatusMessage *statusmsg = xmalloc(sizeof(Ceo__StatusMessage));
    char *message = xmalloc(MAX_MESGSIZE);

    va_start(args, fmt);
    vsnprintf(message, MAX_MESGSIZE, fmt, args);
    va_end(args);

    ceo__status_message__init(statusmsg);
    statusmsg->status = status;
    statusmsg->message = message;

    if (r->n_messages >= MAX_MESSAGES)
        fatal("too many messages");
    r->messages[r->n_messages++] = statusmsg;

    if (status)
        error("%s", message);
    else
        notice("%s", message);

    return status;
}

void response_delete(Ceo__UpdateMailResponse *r) {
    int i;

    for (i = 0; i < r->n_messages; i++) {
        free(r->messages[i]->message);
        free(r->messages[i]);
    }
    free(r->messages);
    free(r);
}

static int check_update_mail(Ceo__UpdateMail *in, Ceo__UpdateMailResponse *out, char *client) {
    int client_office = check_group(client, "office");
    int client_syscom = check_group(client, "syscom");

    notice("update mail uid=%s mail=%s by %s", in->username, in->forward, client);

    if (!in->username)
        return response_message(out, EINVAL, "missing required argument: username");

    int recipient_syscom = check_group(in->username, "syscom");

    if (!client_syscom && !client_office && strcmp(in->username, client))
        return response_message(out, EPERM, "%s not authorized to update mail", client);

    if (recipient_syscom && !client_syscom)
        return response_message(out, EPERM, "denied, recipient is on systems committee");

    /* don't allow office staff to set complicated forwards; in particular | is a security hole */
    if (in->forward) {
        for (char *p = in->forward; *p; p++) {
            switch (*p) {
                case '"':
                case '\'':
                case ',':
                case '|':
                case '$':
                case '/':
                case '#':
                case ':':
                    return response_message(out, EINVAL, "invalid character in forward: %c", *p);
                default:
                    break;
            }

            if (isspace(*p))
                return response_message(out, EINVAL, "invalid character in forward: %c", *p);
        }
    }

    return 0;
}

static int32_t update_mail(Ceo__UpdateMail *in, Ceo__UpdateMailResponse *out, char *client) {
    int32_t chk_stat;
    mode_t mask;

    chk_stat = check_update_mail(in, out, client);
    if (chk_stat)
        return chk_stat;

    mask = umask(0);

    if (in->forward) {
        struct passwd *user = getpwnam(in->username);

        if (!user)
            return response_message(out, errno, "getpwnam: %s: %s", in->username, strerror(errno));

        if (setregid(user->pw_gid, user->pw_gid))
            return response_message(out, errno, "setregid: %s: %s", in->username, strerror(errno));
        if (setreuid(user->pw_uid, user->pw_uid))
            return response_message(out, errno, "setreuid: %s: %s", in->username, strerror(errno));

        char path[1024];

        if (snprintf(path, sizeof(path), "%s/.forward", user->pw_dir) >= sizeof(path))
            return response_message(out, ENAMETOOLONG, "homedir is too long");

        if (unlink(path) && errno != ENOENT)
            return response_message(out, errno, "unlink: %s: %s", path, strerror(errno));

        if (*in->forward) {
            int fd = open(path, O_WRONLY|O_CREAT|O_EXCL, 0644);
            if (fd < 0)
                return response_message(out, errno, "open: %s: %s", path, strerror(errno));

            struct strbuf file_contents = STRBUF_INIT;
            strbuf_addf(&file_contents, "%s\n", in->forward);

            if (full_write(fd, file_contents.buf, file_contents.len))
                response_message(out, errno, "write: %s: %s", path, strerror(errno));

            strbuf_release(&file_contents);

            if (close(fd))
                return response_message(out, errno, "close: %s: %s", path, strerror(errno));

            response_message(out, 0, "successfully updated forward for %s", in->username);
        } else {
            response_message(out, 0, "successfully cleared forward for %s", in->username);
        }
    }

    umask(mask);

    return response_message(out, 0, "finished updating mail for %s", in->username);
}

void cmd_update_mail(void) {
    Ceo__UpdateMail *in_proto;
    Ceo__UpdateMailResponse *out_proto = response_create();
    struct strbuf in = STRBUF_INIT;
    struct strbuf out = STRBUF_INIT;

    if (strbuf_read(&in, STDIN_FILENO, 0) < 0)
        fatalpe("read");

    in_proto = ceo__update_mail__unpack(&protobuf_c_default_allocator,
            in.len, (uint8_t *)in.buf);
    if (!in_proto)
        fatal("malformed update mail message");

    char *client = getenv("CEO_USER");
    if (!client)
        fatal("environment variable CEO_USER is not set");

    update_mail(in_proto, out_proto, client);

    strbuf_grow(&out, ceo__update_mail_response__get_packed_size(out_proto));
    strbuf_setlen(&out, ceo__update_mail_response__pack(out_proto, (uint8_t *)out.buf));

    if (full_write(STDOUT_FILENO, out.buf, out.len))
        fatalpe("write: stdout");

    ceo__update_mail__free_unpacked(in_proto, &protobuf_c_default_allocator);
    response_delete(out_proto);

    strbuf_release(&in);
    strbuf_release(&out);
}

int main(int argc, char *argv[]) {
    prog = xstrdup(basename(argv[0]));
    init_log(prog, LOG_PID, LOG_AUTHPRIV, 0);

    configure();

    cmd_update_mail();

    free_config();
    free(prog);

    return 0;
}
