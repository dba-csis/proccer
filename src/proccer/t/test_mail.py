from __future__ import with_statement

from datetime import datetime
from mock import Mock, patch
from socket import gethostname

from proccer.database import Job
from proccer.notifications import send_mail
from proccer.notifications import mail_for_state
from proccer.notifications import state_change_notification
from proccer.t.testing import setup_module


def setup_function():
    global job
    job = Job(host='snafu.example.com', login='foo', name='bar')
    job.last_seen = job.last_stamp = datetime(1979, 7, 7, 11, 22, 33)
    job.state_id = 1
    job.result = {'ok': True}
    job.rusage = {}
    session.add(job)
    session.flush()

env_from = 'proccer@' + gethostname()
ok_result = {
    'host': 'snafu.example.com',
    'login': 'foo',
    'name': 'bar',
    'result': {'ok': True},
    'clock': 3.14,
    'rusage': {},
    'stamp': '1979-07-07T11:22:33Z',
    'config': {
        'command': '/bin/true',
    },
    'output': 'Hello, World!',
}

devops_mail_patch = patch('proccer.notifications.default_recipient',
                     'devops@example.com')



def test_state_change_notification():
    with patch('proccer.notifications.smtplib') as smtplib:
        smtp = smtplib.SMTP.return_value = Mock()
        with devops_mail_patch:
            state_change_notification(job, ok_result)
        assert smtplib.SMTP.call_args == (('no-such-host',), {}),\
               smtplib.SMTP.call_args
        assert smtp.sendmail.called


def test_send_mail():
    msg = Mock()
    msg.as_string.return_value = 'Hello, World!'
    with devops_mail_patch:
        with patch('smtplib.SMTP') as smtp:
            send_mail(msg, ['bar@example.com'])
    assert msg.as_string.called
    assert msg.as_string.call_args == ((), {}), msg.as_string.call_args
    assert smtp.return_value.sendmail.called
    expected = ((env_from, ['bar@example.com'], 'Hello, World!'), {})
    assert smtp.return_value.sendmail.call_args == expected, \
           smtp.return_value.sendmail.call_args


def test_mail_for_state():
    with devops_mail_patch:
        msg, rcpt = mail_for_state(job, 'ok', ok_result)
    txt = msg.as_string()
    assert rcpt == ['devops@example.com'], repr(rcpt)
    assert '\n  Hello, World!\n' in txt, txt
    assert msg['Subject'] == '[foo@snafu/bar] ok', msg['Subject']


def test_mail_for_state_w_notification():
    job.notify = ['foo@example.com']
    msg, rcpt = mail_for_state(job, 'ok', ok_result)
    txt = msg.as_string()
    assert rcpt == ['foo@example.com'], repr(rcpt)
    assert '\n  Hello, World!\n' in txt, txt
    assert msg['Subject'] == '[foo@snafu/bar] ok', msg['Subject']
