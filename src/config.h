#define CONFIG_FILE "/etc/csc/accounts.cf"

extern char *server_url;
extern char *users_base;
extern char *groups_base;
extern char *sudo_base;

extern char *skeleton_dir;

extern char *member_shell;
extern long member_min_id;
extern long member_max_id;
extern char *member_home;
extern char *member_home_acl;
extern char *member_home_dacl;

extern char *club_shell;
extern long club_min_id;
extern long club_max_id;
extern char *club_home;
extern char *club_home_acl;
extern char *club_home_dacl;

extern char *notify_hook;

extern char *homedir_mode;

extern char *realm;

extern char *admin_principal;
extern char *admin_keytab;

extern char *admin_bind_userid;
extern char *admin_bind_keytab;

extern char *sasl_realm;
extern char *sasl_mech;

extern char *privileged_group;

void configure();
