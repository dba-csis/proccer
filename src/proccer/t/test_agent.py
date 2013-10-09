from __future__ import with_statement

from mock import patch, call
from nose.tools import eq_
import os
import resource
from tempfile import NamedTemporaryFile

from proccer.agent import read_configuration, report, set_memory_limit, \
    default_memory_limit, _in_parent, _in_child
from proccer.t.testing import assert_eq


def test_report():
    with patch('requests.post') as mock:
        report({})

    assert mock.called
    args, kwargs = mock.call_args
    assert_eq(args, ('http://proccer-test/api/1.0/report',))
    assert_eq(kwargs['data'], '{}')


def test_report_no_api():
    with patch('proccer.agent.API_URL', ''):
        with patch('requests.post') as mock:
            report({})

    assert not mock.called


def test_just_commands():
    yaml = '''
        commands:
            t: {command: "true", warn-after: 15 seconds}
    '''
    parsed = read_configuration(yaml)
    expected = {
        'commands': {
            't': {
                'command': 'true',
                'warn-after': '15 seconds',
            }
        }
    }
    assert parsed == expected, parsed


def test_with_overrides():
    yaml = '''
        overrides:
            - match: ".*/t"
              warn-after: "45 seconds"
        commands:
            t: {command: "true", warn-after: 15 seconds}
    '''
    parsed = read_configuration(yaml)
    expected = {
        'commands': {
            't': {
                'command': 'true',
                'warn-after': '45 seconds',
            }
        }
    }
    assert parsed == expected, parsed


def check_memvalue(job_desc):
    '''Check if the correct memory limit is applied'''

    expected_memory_value = job_desc.get('memory-limit', default_memory_limit)

    with patch('resource.setrlimit') as resource_setrlimit:
        set_memory_limit(job_desc)

    eq_(resource_setrlimit.mock_calls,
        [call(resource.RLIMIT_AS, (expected_memory_value, -1))])


def test_memvalue_generator():
    unlimited_job_desc = {
        'command': 'true'
    }
    yield check_memvalue, unlimited_job_desc

    limited_job_desc = {
        'command': 'true',
        'memory-limit': 50000000
    }
    yield check_memvalue, limited_job_desc


def fork_and_wait(name, desc):
    with NamedTemporaryFile() as logfile:
        pid = os.fork()
        if pid:
            return _in_parent(name, desc, pid, logfile)
        else:
            _in_child(name, desc, logfile)


def check_memlimit(memory_bytes):
    job_name = 'jobname'
    command = 'python ./src/proccer/t/test_agent/allocate_memory.py %s'

    job_desc = {
        'command': command % memory_bytes
    }

    r = fork_and_wait(job_name, job_desc)

    assert_eq(r['result']['ok'], memory_bytes < default_memory_limit)
    assert r['rusage']['ru_maxrss'] < default_memory_limit


def test_memlimit_generator():
    for limit_m in (900, 1100):
        yield check_memlimit, limit_m * 1024 * 1024
