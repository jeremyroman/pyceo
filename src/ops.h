struct op {
    char *name;
    uint32_t id;
    int local;
    char *hostname;
    char *path;
    struct in_addr addr;
    struct op *next;
    char *user;
};

void setup_ops(void);
void free_ops(void);
struct op *find_op(const char *name);
struct op *get_local_op(uint32_t id);
