import os
from socket import gethostname
import subprocess

# Valid Nagios (i.e. send_nsca) status codes.
status_names = ['ok', 'warning', 'critical', 'unknown']
OK, WARN, CRIT, UNKNOWN = status_codes = range(4)
status_code = dict(zip(status_names, status_codes))

nsca_host = os.environ.get('NSCA_HOST')
nsca_cfg = os.environ.get('SEND_NSCA_CFG',
                          '/usr/local/etc/nagios/send_nsca.cfg')
nsca_cmd = 'send_nsca -H %s -c %s > /dev/null' % (nsca_host, nsca_cfg)

# Hostname we use in send_nsca service-checks
hostname = os.environ.get('NAGIOS_HOSTNAME',
                          gethostname().split('.')[0])
# Service name we use in send_nsca service-checks
service = 'proccer'

def format_nsca(status, message):
    pieces = [
        hostname,
        service,
        str(status_code[status]),
        message,
    ]
    line = '\t'.join(pieces) + '\n'
    return line

def send_nsca(status, message):
    if not nsca_host:
        return

    child = subprocess.Popen(nsca_cmd.split(),
                             stdin=subprocess.PIPE)
    child.communicate(format_nsca(status, message))
    if not child.wait() == 0:
        raise RuntimeError('send_nsca failed')
