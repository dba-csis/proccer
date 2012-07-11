from __future__ import with_statement

from mock import patch
from StringIO import StringIO

from proccer.agent import read_configuration, report
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
