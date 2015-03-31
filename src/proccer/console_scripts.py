import atexit
import logging
import logging.config
from optparse import OptionParser
import os
from lockfile import FileLock, LockError
from StringIO import StringIO
import sys

default_log_file = os.path.expanduser(os.environ.get('PROCCER_LOG',
                                                     '~/proccer.log'))

run_processes_opts = OptionParser('Usage: %prog [options] proccess(es)')
run_processes_opts.add_option('-c', '--configuration',
                              default='proccer.yaml')
run_processes_opts.add_option('-v', '--verbose',
                              action='count', dest='verbosity', default=0)
run_processes_opts.add_option('--logging-configuration',
                              default=os.environ.get('PROCCER_LOG_CONFIG'))
run_processes_opts.add_option('--log-file', default=default_log_file)


log_file_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

log_config = '''
[loggers]
keys=root

[handlers]
keys=console,file

[formatters]
keys=formatter

[logger_root]
level=DEBUG
handlers=console,file

[handler_console]
class=StreamHandler
level=%(level)s
formatter=formatter
args=(sys.stderr,)

[handler_file]
class=FileHandler
level=DEBUG
formatter=formatter
args=('%(path)s', 'a', 'utf-8')

[formatter_formatter]
format=%%(asctime)s - %%(name)s - %%(levelname)s - %%(message)s
datefmt=
'''


def rotate_log_file(path):
    try:
        lockfile = FileLock(path + '.lock')
        lockfile.acquire(timeout=0)
    except LockError:
        return

    try:
        if os.path.exists(path) and os.stat(path).st_size > 1024 * 1024:
            os.rename(path, path + '.1')
    finally:
        lockfile.release()


def configure_logging(opts):
    level = logging.ERROR - 10 * opts.verbosity

    if opts.logging_configuration:
        conf_path = os.path.expanduser(opts.logging_configuration)
        logging.config.fileConfig(conf_path)

    elif opts.log_file:
        assert "'" not in opts.log_file
        logging.config.fileConfig(StringIO(log_config % {
            'path': opts.log_file,
            'level': logging.getLevelName(level),
        }))

        atexit.register(rotate_log_file, opts.log_file)

    else:
        logging.basicConfig(level=level)

    return logging.getLogger('proccer')


def run_processes():
    opts, args = run_processes_opts.parse_args()
    log = configure_logging(opts)

    from proccer import agent
    conf = agent.load_configuration(opts.configuration)
    for name in args:
        try:
            log.debug('[%s] starting', name)
            result = agent.run_process(conf, name)
            if result:
                agent.log_for(result)
                agent.report(result)
                agent.raise_for(result)
            log.debug('[%s] done', name)

        except agent.ProcessError, e:
            log.error('[%s] %s', name, e.args[0])
            sys.exit(1)
