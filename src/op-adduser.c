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
#include <sys/wait.h>

#include "util.h"
#include "net.h"
#include "ceo.pb-c.h"
#include "config.h"
#include "gss.h"
#include "krb5.h"
#include "ldap.h"
#include "kadm.h"
#include "daemon.h"
#include "strbuf.h"

char *prog;

static const int MAX_MESSAGES = 32;
static const int MAX_MESGSIZE = 512;

char *user_types[] = {
    [CEO__ADD_USER__TYPE__MEMBER] = "member",
    [CEO__ADD_USER__TYPE__CLUB] = "club",
};

Ceo__AddUserResponse *response_create(void) {
    Ceo__AddUserResponse *r = xmalloc(sizeof(Ceo__AddUserResponse));
    ceo__add_user_response__init(r);
    r->n_messages = 0;
    r->messages = xmalloc(MAX_MESSAGES *  sizeof(Ceo__StatusMessage *));
    return r;
}

int32_t response_message(Ceo__AddUserResponse *r, int32_t status, char *fmt, ...) {
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

void response_delete(Ceo__AddUserResponse *r) {
    int i;

    for (i = 0; i < r->n_messages; i++) {
        free(r->messages[i]->message);
        free(r->messages[i]);
    }
    free(r->messages);
    free(r);
}


static int check_adduser(Ceo__AddUser *in, Ceo__AddUserResponse *out, char *client) {
    int office = check_group(client, "office");
    int syscom = check_group(client, "syscom");

    notice("adding uid=%s cn=%s by %s", in->username, in->realname, client);

    if (!office && !syscom)
        return response_message(out, EPERM, "%s not authorized to create users", client);

    if (!in->username)
        return response_message(out, EINVAL, "missing required argument: username");
    if (!in->realname)
        return response_message(out, EINVAL, "missing required argument: realname");

    if (in->type == CEO__ADD_USER__TYPE__MEMBER) {
        if (!in->password)
            return response_message(out, EINVAL, "missing required argument: password");
    } else if (in->type == CEO__ADD_USER__TYPE__CLUB) {
        if (in->password)
            return response_message(out, EINVAL, "club accounts cannot have passwords");
        if (in->program)
            return response_message(out, EINVAL, "club accounts cannot have programs");
    } else {
        return response_message(out, EINVAL, "invalid user type: %d", in->type);
    }

    if (getpwnam(in->username) != NULL)
        return response_message(out, EEXIST, "user %s already exists", in->username);

    if (getgrnam(in->username) != NULL)
        return response_message(out, EEXIST, "group %s already exists", in->username);

    if (ceo_user_exists(in->username))
        return response_message(out, EEXIST, "user %s already exists in LDAP", in->username);

    if (ceo_group_exists(in->username))
        return response_message(out, EEXIST, "group %s already exists in LDAP", in->username);

    return 0;
}

static void adduser_spam(Ceo__AddUser *in, Ceo__AddUserResponse *out, char *client, char *prog, int status) {
    char *argv[] = {
        notify_hook, prog, client,
        in->username, in->realname, in->program ?: "",
        status ? "failure" : "success", NULL
    };

    struct strbuf message = STRBUF_INIT;
    for (int i = 0; i < out->n_messages; i++)
        strbuf_addf(&message, "%s\n", out->messages[i]->message);

    spawnv_msg(notify_hook, argv, &message);
    strbuf_release(&message);
}

static int32_t addmember(Ceo__AddUser *in, Ceo__AddUserResponse *out) {
    char homedir[1024];
    int user_stat, group_stat, krb_stat;
    int id;

    if (snprintf(homedir, sizeof(homedir), "%s/%s",
                 member_home, in->username) >= sizeof(homedir))
        fatal("homedir overflow");

    if ((id = ceo_new_uid(member_min_id, member_max_id)) <= 0)
        fatal("no available uids in range [%ld, %ld]", member_min_id, member_max_id);

    if ((krb_stat = ceo_del_princ(in->username)))
        return response_message(out, EEXIST, "unable to overwrite orphaned kerberos principal %s", in->username);

    if ((krb_stat = ceo_add_princ(in->username, in->password)))
        return response_message(out, EKERB, "unable to create kerberos principal %s", in->username);
    response_message(out, 0, "successfully created principal");

    if ((user_stat = ceo_add_user(in->username, users_base, "member", in->realname, homedir,
            member_shell, id, "program", in->program, NULL)))
        return response_message(out, ELDAP, "unable to create ldap account %s", in->username);
    response_message(out, 0, "successfully created ldap account");

    /* errors that occur after this point are not fatal  */

    if ((group_stat = ceo_add_group(in->username, groups_base, id)))
        response_message(out, ELDAP, "unable to create ldap group %s", in->username);
    else
        response_message(out, 0, "successfully created ldap group");

    return krb_stat || user_stat || group_stat;
}

static int32_t addclub(Ceo__AddUser *in, Ceo__AddUserResponse *out) {
    char homedir[1024];
    int krb_stat, user_stat, group_stat, sudo_stat;
    int id;

    if (snprintf(homedir, sizeof(homedir), "%s/%s",
                 club_home, in->username) >= sizeof(homedir))
        fatal("homedir overflow");

    if ((id = ceo_new_uid(club_min_id, club_max_id)) <= 0)
        fatal("no available uids in range [%ld, %ld]", club_min_id, club_max_id);

    if ((krb_stat = ceo_del_princ(in->username)))
        return response_message(out, EKERB, "unable to clear principal %s", in->username);

    if ((user_stat = ceo_add_user(in->username, users_base, "club", in->realname, homedir,
            club_shell, id, NULL)))
        return response_message(out, ELDAP, "unable to create ldap account %s", in->username);
    response_message(out, 0, "successfully created ldap account");

    /* errors that occur after this point are not fatal  */

    if ((group_stat = ceo_add_group(in->username, groups_base, id)))
        response_message(out, ELDAP, "unable to create ldap group %s", in->username);
    else
        response_message(out, 0, "successfully created ldap group");

    if ((sudo_stat = ceo_add_group_sudo(in->username, sudo_base)))
        response_message(out, ELDAP, "unable to create ldap sudoers %s", in->username);
    else
        response_message(out, 0, "successfully created ldap sudoers");

    return user_stat || group_stat || sudo_stat;
}

static int32_t adduser(Ceo__AddUser *in, Ceo__AddUserResponse *out, char *client) {
    int32_t chk_stat, status;
    char *prog;

    chk_stat = check_adduser(in, out, client);
    if (chk_stat)
        return chk_stat;

    if (in->type == CEO__ADD_USER__TYPE__MEMBER) {
        status = addmember(in, out);
        prog = "addmember";
    } else if (in->type == CEO__ADD_USER__TYPE__CLUB) {
        status = addclub(in, out);
        prog = "addclub";
    } else {
        fatal("unknown user type %d", in->type);
    }

    if (status)
        response_message(out, 0, "there were failures, please contact systems committee");

    adduser_spam(in, out, client, prog, status);

    return status;
}

void cmd_adduser(void) {
    Ceo__AddUser *in_proto;
    Ceo__AddUserResponse *out_proto = response_create();
    struct strbuf in = STRBUF_INIT;
    struct strbuf out = STRBUF_INIT;

    if (strbuf_read(&in, STDIN_FILENO, 0) < 0)
        fatalpe("read");

    in_proto = ceo__add_user__unpack(&protobuf_c_default_allocator,
            in.len, (uint8_t *)in.buf);
    if (!in_proto)
        fatal("malformed add user message");

    char *client = getenv("CEO_USER");
    if (!client)
        fatal("environment variable CEO_USER is not set");

    adduser(in_proto, out_proto, client);

    strbuf_grow(&out, ceo__add_user_response__get_packed_size(out_proto));
    strbuf_setlen(&out, ceo__add_user_response__pack(out_proto, (uint8_t *)out.buf));
    full_write(STDOUT_FILENO, out.buf, out.len);

    ceo__add_user__free_unpacked(in_proto, &protobuf_c_default_allocator);
    response_delete(out_proto);

    strbuf_release(&in);
    strbuf_release(&out);
}

int main(int argc, char *argv[]) {
    prog = xstrdup(basename(argv[0]));
    init_log(prog, LOG_PID, LOG_AUTHPRIV);

    configure();

    if (setenv("KRB5CCNAME", "MEMORY:adduser", 1))
        fatalpe("setenv");

    ceo_krb5_init();
    ceo_krb5_auth(admin_bind_userid);
    ceo_ldap_init();
    ceo_kadm_init();

    cmd_adduser();

    ceo_kadm_cleanup();
    ceo_ldap_cleanup();
    ceo_krb5_deauth();
    ceo_krb5_cleanup();

    free_config();
    free(prog);

    return 0;
}
