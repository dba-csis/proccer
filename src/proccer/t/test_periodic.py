from __future__ import with_statement

from datetime import datetime, timedelta
from mock import patch

from proccer.database import Job
from proccer.periodic import main
from proccer.t.testing import setup_module

def test_periodic():
    still_bad_job = Job.create(session, 'foo', 'bar', 'baz')
    still_bad_job.last_seen = still_bad_job.last_stamp = datetime(1979, 7, 7)
    still_bad_job.state = 'error'
    still_bad_job.warn_after = timedelta(seconds=1)

    silent_bad_job = Job.create(session, 'foo', 'bar', 'baz')
    silent_bad_job.last_seen = silent_bad_job.last_stamp = datetime(1979, 7, 7)
    silent_bad_job.state = 'error'
    silent_bad_job.warn_after = None

    still_late_job = Job.create(session, 'foo', 'bar', 'baz')
    still_late_job.last_seen = still_late_job.last_stamp = datetime(1979, 7, 7)
    still_late_job.state = 'error'
    still_late_job.warn_after = timedelta(seconds=1)

    session.flush()

    # FIXME - This needs real tests!
    with patch('proccer.notifications.smtplib'):
        main()
