from __future__ import with_statement

from copy import deepcopy
from datetime import timedelta
import jsonlib as json
from mock import Mock, patch

from proccer.agent import _get_result, raise_for
from proccer.database import Job
from proccer.database import update_proccer_job
from proccer.t.testing import setup_module, assert_eq
from proccer.t.test_mail import ok_result


default_recipient_patch = patch('proccer.notifications.default_recipient',
                                'devops@example.com')

send_mail_patch = patch('proccer.notifications.send_mail')

def test_update_proccer_job_new_error():
    result = deepcopy(ok_result)
    result['result']['ok'] = False

    with default_recipient_patch:
        with send_mail_patch as mock:
            update_proccer_job(session, result)

    assert mock.call_count == 1, mock.call_count
    msg, recipient = mock.call_args[0]
    assert_eq(msg['Subject'], '[foo@snafu/bar] error')


def test_update_proccer_job():
    with default_recipient_patch:
        with send_mail_patch as mock:
            job = update_proccer_job(session, ok_result)
            assert job
            assert update_proccer_job(session, ok_result) is job

    assert mock.call_count == 1, mock.call_count
    msg, recipient = mock.call_args[0]
    assert_eq(msg['Subject'], '[foo@snafu/bar] ok')


def test_update_proccer_job_w_warn_after():
    job = update_proccer_job(session, ok_result)
    assert job.warn_after is None, repr(job.warn_after)

    result = deepcopy(ok_result)
    result['config']['warn-after'] = '15 seconds'

    update_proccer_job(session, result)
    assert job.warn_after == timedelta(seconds=15), repr(job.warn_after)


def test_update_proccer_job_w_notify():
    job = update_proccer_job(session, ok_result)
    assert job.notify is None, repr(job.notify)

    result = deepcopy(ok_result)
    ok_result['config']['notify'] = ['foo@example.com', 'bar@example.com']

    job = update_proccer_job(session, ok_result)
    assert job.notify == ['foo@example.com', 'bar@example.com'], job.notify


def test_update_job_state():
    from nose.plugins.skip import SkipTest
    raise SkipTest

    with default_recipient_patch:
        with patch('proccer.notifications.smtplib') as smtplib:
            smtp = smtplib.SMTP.return_value = Mock()

            job = update_proccer_job(session, ok_result)
            update_job_state(session, job.id, 1, ok_result)
            assert not smtp.sendmail.called

        with patch('proccer.notifications.smtplib') as smtplib:
            smtp = smtplib.SMTP.return_value = Mock()

            update_job_state(session, job.id, 2, ok_result)
            assert smtp.sendmail.called

        with patch('proccer.notifications.smtplib') as smtplib:
            smtp = smtplib.SMTP.return_value = Mock()

            update_job_state(session, job.id, 2, ok_result)
            assert not smtp.sendmail.called

        with patch('proccer.notifications.smtplib') as smtplib:
            smtp = smtplib.SMTP.return_value = Mock()

            update_job_state(session, job.id, 3, None)
            assert smtp.sendmail.called
