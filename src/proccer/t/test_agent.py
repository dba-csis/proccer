from __future__ import with_statement

from math import pow
from mock import patch, call
from nose.tools import eq_
import os
import resource
from tempfile import NamedTemporaryFile

from proccer.agent import (read_configuration,
                           report,
                           memory_size_human_to_bytes,
                           set_memory_limit,
                           default_memory_limit,
                           _in_parent,
                           _in_child)
from proccer.t.testing import assert_eq, assert_raises


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


def test_memory_conversion():
    eq_(memory_size_human_to_bytes('1'), 1)
    eq_(memory_size_human_to_bytes('1k'), 1024)
    eq_(memory_size_human_to_bytes('1K'), 1024)
    eq_(memory_size_human_to_bytes('1 k'), 1024)
    eq_(memory_size_human_to_bytes('1 K'), 1024)
    eq_(memory_size_human_to_bytes('1kb'), 1024)
    eq_(memory_size_human_to_bytes('1KB'), 1024)
    eq_(memory_size_human_to_bytes('1 kb'), 1024)
    eq_(memory_size_human_to_bytes('1 KB'), 1024)
    eq_(memory_size_human_to_bytes('1  k'), 1024)
    eq_(memory_size_human_to_bytes('1M'), pow(1024, 2))
    eq_(memory_size_human_to_bytes('1MB'), pow(1024, 2))
    eq_(memory_size_human_to_bytes('1G'), pow(1024, 3))
    eq_(memory_size_human_to_bytes('1GB'), pow(1024, 3))
    eq_(memory_size_human_to_bytes('1T'), pow(1024, 4))
    eq_(memory_size_human_to_bytes('1TB'), pow(1024, 4))
    eq_(memory_size_human_to_bytes('1P'), pow(1024, 5))
    eq_(memory_size_human_to_bytes('1PB'), pow(1024, 5))
    eq_(memory_size_human_to_bytes('1E'), pow(1024, 6))
    eq_(memory_size_human_to_bytes('1EB'), pow(1024, 6))
    eq_(memory_size_human_to_bytes('1Z'), pow(1024, 7))
    eq_(memory_size_human_to_bytes('1ZB'), pow(1024, 7))
    eq_(memory_size_human_to_bytes('1Y'), pow(1024, 8))
    eq_(memory_size_human_to_bytes('1YB'), pow(1024, 8))
    eq_(memory_size_human_to_bytes('2.5 GB'), int(2.5 * pow(1024, 3)))


def test_memory_read_conf_int():
    yaml = '''
        commands:
            t: {command: "true", memory-limit: 50000000}
    '''
    parsed = read_configuration(yaml)
    expected = {
        'commands': {
            't': {
                'command': 'true',
                'memory-limit': 50000000,
            }
        }
    }
    eq_(parsed, expected)


def test_memory_read_conf_human():
    yaml = '''
        commands:
            t: {command: "true", memory-limit: '50M'}
    '''
    parsed = read_configuration(yaml)
    expected = {
        'commands': {
            't': {
                'command': 'true',
                'memory-limit': '50M',
            }
        }
    }
    eq_(parsed, expected)


def check_memvalue(job_desc):
    '''Check if the correct memory limit is applied'''

    specified_memory_value = job_desc.get('memory-limit', default_memory_limit)
    if isinstance(specified_memory_value, int):
        expected_memory_value = specified_memory_value
    else:
        expected_memory_value = \
            memory_size_human_to_bytes(specified_memory_value)

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

    human_readable_job_desc = {
        'command': 'true',
        'memory-limit': '50M'
    }
    yield check_memvalue, human_readable_job_desc


def check_memory_invalid(invalid_job_desc):
    with patch('resource.setrlimit'):
        with assert_raises(Exception):
            set_memory_limit(invalid_job_desc)


def test_memory_invalid():
    '''Tests if the default memory limit is applyed if the specified value
    is invalid'''

    invalid_unit_job = {
        'command': 'true',
        'memory-limit': '666 zillion'
    }
    yield check_memory_invalid, invalid_unit_job

    invalid_value_job = {
        'command': 'true',
        'memory-limit': '6.6.6 MB'
    }
    yield check_memory_invalid, invalid_value_job

    empty_field_job = {
        'commad': 'true',
        'memory-limit': ''
    }
    yield check_memory_invalid, empty_field_job

    invalid_format_job = {
        'commad': 'true',
        'memory-limit': '1m2m3m4m'
    }
    yield check_memory_invalid, invalid_format_job


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
