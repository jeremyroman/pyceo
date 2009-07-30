#include <krb5.h>
#include <com_err.h>

extern char *prog;

extern krb5_context context;

void ceo_krb5_init();
void ceo_krb5_cleanup();

void ceo_krb5_auth(char *);
void ceo_krb5_deauth();

int ceo_read_password(char *, unsigned int, int);
