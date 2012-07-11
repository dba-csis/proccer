from __future__ import with_statement

from datetime import datetime
from mock import Mock, patch
from socket import gethostname

from proccer.database import Job
from proccer.mail import send_mail
from proccer.mail import mail_for_state
from proccer.mail import state_change_notification
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


def test_state_change_notification():
    with patch('proccer.mail.smtplib') as smtplib:
        smtp = smtplib.SMTP.return_value = Mock()
        with patch('proccer.mail.default_recipient', 'devops@example.com'):
            state_change_notification(job, ok_result)
        assert smtplib.SMTP.call_args == (('no-such-host',), {}),\
               smtplib.SMTP.call_args
        assert smtp.sendmail.called


def test_send_mail():
    msg = Mock()
    msg.as_string.return_value = 'Hello, World!'
    with patch('proccer.mail.default_recipient', 'devops@example.com'):
        with patch('smtplib.SMTP') as smtp:
            send_mail(msg, ['bar@example.com'])
    assert msg.as_string.called
    assert msg.as_string.call_args == ((), {}), msg.as_string.call_args
    assert smtp.return_value.sendmail.called
    expected = ((env_from, ['bar@example.com'], 'Hello, World!'), {})
    assert smtp.return_value.sendmail.call_args == expected, \
           smtp.return_value.sendmail.call_args


def test_mail_for_state():
    with patch('proccer.mail.default_recipient', 'devops@example.com'):
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
