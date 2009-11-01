#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <gssapi/gssapi.h>

typedef struct sockaddr sa;

extern struct strbuf fqdn;
extern void setup_fqdn(void);
extern void free_fqdn(void);

enum {
    MSG_AUTH    = 0x8000000,
    MSG_EXPLODE = 0x8000001,
};

#define EKERB -2
#define ELDAP -3
#define EHOME -4

int ceo_receive_message(int sock, struct strbuf *msg, uint32_t *msgtype);
int ceo_send_message(int sock, void *msg, size_t len, uint32_t msgtype);
