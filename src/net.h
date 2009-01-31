#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netinet/sctp.h>
#include <arpa/inet.h>
#include <gssapi/gssapi.h>

#if ! defined(SCTP_ADDR_CONFIRMED) && defined(__linux__)
#define SCTP_ADDR_CONFIRMED 5
#endif

void notification_dbg(char *);

#ifdef SCTP_ADAPTION_LAYER
#define sctp_adaptation_layer_event sctp_adaption_layer_event
#define sn_adaptation_event sn_adaption_event
#define sai_adaptation_ind sai_adaption_ind
#define SCTP_ADAPTATION_INDICATION SCTP_ADAPTION_INDICATION
#endif

typedef struct sockaddr sa;

extern struct strbuf fqdn;
extern void setup_fqdn(void);
extern void free_fqdn(void);

struct sctp_meta {
    struct sockaddr_storage from;
    socklen_t fromlen;
    struct sctp_sndrcvinfo sinfo;
};

enum {
    MSG_AUTH    = 0x8000000,
    MSG_EXPLODE = 0x8000001,
};

#ifdef MSG_ABORT
#define SCTP_ABORT MSG_ABORT
#define SCTP_EOF   MSG_EOF
#endif

#define EKERB -2
#define ELDAP -3

int receive_one_message(int sock, struct sctp_meta *msg_meta, struct strbuf *msg);
