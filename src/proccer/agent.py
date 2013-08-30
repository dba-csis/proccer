from __future__ import with_statement

from contextlib import closing, contextmanager
from datetime import datetime
import errno
import jsonlib as json
from lockfile import FileLock, LockError
import logging
import os
import re
import requests
import signal
from socket import gethostname
from tempfile import NamedTemporaryFile
import time
import traceback
import yaml

log = logging.getLogger('proccer')

API_URL = os.environ.get('PROCCER_API_URL', '').rstrip('/')

signal_name = dict((k, v)
                   for v, k in signal.__dict__.iteritems()
                   if v.startswith('SIG'))


class ProcessError(Exception):
    pass


def read_configuration(fp):
    parsed = yaml.load(fp)

    overrides = parsed.pop('overrides', [])
    for override in overrides:
        m = re.compile(override.pop('match'))
        for name, desc in parsed['commands'].items():
            job_id = '%s@%s/%s' % (os.environ.get('USER', ''),
                                   gethostname(),
                                   name)
            if m.match(job_id):
                desc.update(override)

    return parsed


def load_configuration(path):
    return read_configuration(open(path))


def run_process(conf, name):
    commands = conf.get('commands', {})
    desc = commands.get(name)
    if not desc:
        raise ProcessError('No such process: %s' % name)

    try:
        with _grab_lock(name, desc):
            with closing(NamedTemporaryFile()) as logfile:
                pid = os.fork()
                if pid:
                    return _in_parent(name, desc, pid, logfile)
                else:
                    _in_child(name, desc, logfile)

    except LockError:
        if desc.get('lockfile', {}).get('silent'):
            log.debug('[%s] silently ignoring lock-file timeout', name)
            return
        raise ProcessError('lock-file timeout')


def _in_parent(name, desc, pid, logfile):
    # Install signal handlers
    def _signalled(signo, frames):
        log.debug('received signal %s, passing it on to child',
                  signal_name.get(signo, str(signo)))
        os.killpg(pid, signal.SIGTERM)

    signal.signal(signal.SIGALRM, _signalled)
    signal.signal(signal.SIGINT, _signalled)
    signal.signal(signal.SIGTERM, _signalled)

    # Setup timeout (via SIGALRM)
    timeout = desc.get('timeout')
    if timeout:
        signal.alarm(timeout)

    before = time.time()
    _, status, rusage = _wait_for(pid)
    after = time.time()

    # Clear timeout
    if timeout:
        signal.alarm(0)

    # Read stdout/stderr log and return result
    logfile.seek(0, 0)
    output = logfile.read().decode('utf-8', 'replace')

    return {
        'stamp': datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ'),
        'name': name,
        'host': gethostname(),
        'login': os.environ.get('LOGNAME', ''),
        'config': desc,
        'result': _get_result(status),
        'rusage': dictify_rusage(rusage),
        'clock': after - before,
        'output': output,
    }


def _wait_for(pid):
    # Keep retrying os.wait4 until it does not get interrupted.
    while True:
        try:
            return os.wait4(pid, 0)
        except OSError as e:
            if e.errno != errno.EINTR:
                raise


def _in_child(name, desc, logfile):
    try:
        # We want our own process-group.
        os.setsid()

        # Open stdin, then stdout and stderr, and finally close everything
        # else.  Opening files in this order ensured we're never without
        # somewhere to emit errors.
        fd = os.open(os.devnull, os.O_RDONLY)
        if fd != 0:
            os.dup2(fd, 0)

        os.dup2(logfile.fileno(), 1)
        os.dup2(1, 2)

        _close_all_fds(min=3)

        # Go!
        os.environ.update(desc.get('env', {}))
        os.execvpe('sh', ['sh', '-c', desc['command']],
                   os.environ)

    except:
        # Log what happened here.
        traceback.print_exc()

    finally:
        # If we fall through to here we must fail the child-process, or
        # everything will end in tears and recriminations.
        os._exit(117)


def _close_all_fds(min=0):
    try:
        maxfd = os.sysconf("SC_OPEN_MAX")
    except (AttributeError, ValueError):
        log.warn('SC_OPEN_MAX not defined')
        maxfd = 1024

    for fd in range(min, maxfd):
        try:
            os.close(fd)
        except EnvironmentError:
            pass


@contextmanager
def _grab_lock(name, desc):
    lck_desc = desc.get('lockfile', {})
    path = lck_desc.get('path', os.path.join('~', name))
    timeout = lck_desc.get('timeout', 0)

    locked = False
    try:
        lockfile = FileLock(os.path.expanduser(path))
        lockfile.acquire(timeout=timeout)
        locked = True
        yield

    finally:
        if locked:
            lockfile.release()


def log_for(result):
    log.debug('[%s] result: %r', result['name'], result)
    log.info('[%s] took %.2fs', result['name'], result['clock'])


def report(result):
    if not API_URL:
        return

    try:
        headers = {'Content-Type': 'application/json; charset=utf-8'}
        report_url = API_URL + '/1.0/report'
        r = requests.post(report_url,
                          data=json.dumps(result),
                          headers=headers)
        r.raise_for_status()
    except Exception:
        log.warn('error delivering job-status %r',
                 result,
                 exc_info=True)


def raise_for(result):
    'Raise ProcessError if process did not exit OK.'
    result, reason = result['result'], result['result'].get('reason')
    if result['ok']:
        return
    elif reason == 'signal':
        raise ProcessError('terminated by signal %d' % result['signo'])
    elif reason == 'exit':
        raise ProcessError('non-zero exit: %d' % result['code'])
    else:
        raise ProcessError('died mysteriously: %d' % result['status'])


def _get_result(st):
    exited, status = os.WIFEXITED(st), os.WEXITSTATUS(st)
    signalled, signo = os.WIFSIGNALED(st), os.WTERMSIG(st)

    if exited and status == 0:
        return {'ok': True}
    elif signalled:
        return {'ok': False, 'reason': 'signal', 'signo': signo}
    elif status != 0:
        return {'ok': False, 'reason': 'exit', 'code': status}
    else:
        return {'ok': False, 'reason': 'unknown', 'status': st}


def dictify_rusage(rusage):
    return dict((key, getattr(rusage, key))
                for key in rusage_keys)

rusage_keys = '''ru_utime ru_stime ru_maxrss ru_ixrss ru_idrss ru_isrss
                 ru_minflt ru_majflt ru_nswap ru_inblock ru_oublock ru_msgsnd
                 ru_msgrcv ru_nsignals ru_nvcsw ru_nivcsw'''.split()
