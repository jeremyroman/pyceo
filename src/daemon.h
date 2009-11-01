/* dmain.c */
extern int terminate;
extern int fatal_signal;

/* dslave.c */
void slave_main(int sock, struct sockaddr *addr);
void setup_slave(void);
