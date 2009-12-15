import os, syslog, grp

def response_message(response, status, message):
    if status:
        priority = syslog.LOG_ERR
    else:
        priority = syslog.LOG_INFO
    syslog.syslog(priority, message)
    msg = response.messages.add()
    msg.status = status
    msg.message = message
    return status

def get_ceo_user():
    user = os.environ.get('CEO_USER')
    if not user:
        raise Exception("environment variable CEO_USER not set");
    return user

def check_group(user, group):
    try:
        return user in grp.getgrnam(group).gr_mem
    except KeyError:
        return False
