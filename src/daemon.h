/* dmain.c */
extern int terminate;
extern int fatal_signal;

/* dslave.c */
void slave_main(int sock, struct sockaddr *addr);
void setup_slave(void);

/* builtin-adduser.c */
extern void builtin_adduser(struct sctp_meta *in, struct sctp_meta *out);
