#define LDAP_DEFAULT_PROTOCOL LDAP_VERSION3

int ceo_add_user(char *, char *, char *, char *, char *, char *, int, ...);
int ceo_add_group(char *, char *, int);
int ceo_add_group_sudo(char *, char *);
int ceo_new_uid(int, int);

void ceo_ldap_init();
void ceo_ldap_cleanup();

int ceo_user_exists(char *);
