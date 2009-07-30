#include <sys/acl.h>

#define CLUB_ACL "u::rwx,g::r-x,o::r-x,g:%d:rwx,m::rwx"

int ceo_create_home(char *homedir, char *skel, uid_t uid, gid_t gid, char *access_acl, char *default_acl);
