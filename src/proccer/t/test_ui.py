from __future__ import with_statement

from datetime import datetime
from mock import patch
from werkzeug.test import Client
from werkzeug.wrappers import BaseResponse

from proccer.database import Job, JobResult
from proccer.t.testing import setup_module
from proccer.t.test_mail import ok_result
from proccer.app import app


def test_index():
    job = Job.create(session, 'foo', 'bar', 'baz')
    job.state = 'ok'
    job.last_stamp = job.last_seen = datetime(1979, 7, 9)

    client = Client(app, BaseResponse)
    resp = client.get('/')
    assert resp.status_code == 200


def test_get_job():
    job = Job.create(session, 'foo', 'bar', 'baz')
    job.state = 'ok'
    job.last_stamp = job.last_seen = datetime(1979, 7, 9)
    session.flush()

    result = JobResult.create(job=job, clock_ms=117,
                              result={}, rusage={}, output='Hello, World!')
    session.flush()

    client = Client(app, BaseResponse)
    resp = client.get('/job/%d/' % job.id)
    assert resp.status_code == 200
    assert 'Hello, World!' in resp.data
