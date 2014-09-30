from __future__ import with_statement

import jsonlib as json
from mock import patch
from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from proccer.app import app
from proccer.database import Job, JobResult
from proccer.t.testing import setup_module
from proccer.t.test_mail import ok_result


def test_post_new_event():
    client = Client(app, BaseResponse)
    with patch('proccer.notifications.smtplib') as smtplib:
        resp = client.post('/api/1.0/report',
                           data=json.dumps(ok_result),
                           headers={'Content-Type': 'application/json'})

    assert resp.status_code == 200, repr(resp.status, resp.data)
    assert session.query(Job).count() == 1
    assert session.query(JobResult).count() == 1
