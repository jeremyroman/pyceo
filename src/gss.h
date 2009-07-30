#include <gssapi/gssapi.h>
#include <gssapi/gssapi_krb5.h>

void server_acquire_creds(const char *service);
void client_acquire_creds(const char *service, const char *hostname);
void gss_fatal(char *msg, OM_uint32 maj_stat, OM_uint32 min_stat);
int process_server_token(gss_buffer_t incoming_tok, gss_buffer_t outgoing_tok);
int process_client_token(gss_buffer_t incoming_tok, gss_buffer_t outgoing_tok);
int initial_client_token(gss_buffer_t outgoing_tok);
char *client_principal(void);
char *client_username(void);
void free_gss(void);
