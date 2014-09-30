'Module for various periodic checks.'

from __future__ import with_statement

from datetime import datetime, timedelta
import logging
import logging.config
import os

from proccer.database import session_manager
from proccer.database import Job, JobResult, job_state_id
from proccer.notifications import (state_change_notification,
                                   repeat_notification)

log = logging.getLogger('proccer')

STILL_BAD_INTERVAL = timedelta(seconds=6 * 60 * 60)
OLD_RESULT_INTERVAL = timedelta(days=7)


def send_lateness_notifications(session):
    'Send warnings about any jobs that are late.'

    now = datetime.utcnow()
    late = (session
                .query(Job)
                .filter(Job.deleted == None)
                .filter(Job.last_seen + Job.warn_after < now)
                .filter(Job.state_id == job_state_id['ok']))

    for job in late:
        log.debug('late: %r', job)
        job.last_stamp = now
        job.state = 'late'
        state_change_notification(job, None)


def send_still_bad_notifications(session):
    'Send warnings about any jobs that have been not-ok for > 6 hours.'

    now = datetime.utcnow()
    still_bad = (session
                    .query(Job)
                    .filter(Job.deleted == None)
                    .filter(Job.last_stamp + STILL_BAD_INTERVAL < now)
                    .filter(Job.state_id != job_state_id['ok'])
                    .filter(Job.warn_after != None))

    for job in still_bad:
        log.debug('still not-good: %r', job)
        job.last_stamp = now
        repeat_notification(job)


def delete_old_results(session):
    'Delete proccer results older than one week.'

    now = datetime.utcnow()
    old_results = (session
                    .query(JobResult)
                    .filter(JobResult.stamp < now - OLD_RESULT_INTERVAL))
    old_results.delete()


def main():
    log.debug('doing periodic tasks')
    with session_manager() as session:
        send_lateness_notifications(session)
        send_still_bad_notifications(session)
        delete_old_results(session)

if __name__ == '__main__':
    log_conf = os.environ.get('LOGGING_CONFIGURATION')
    if log_conf:
        logging.config.fileConfig(log_conf, disable_existing_loggers=0)
    else:
        logging.basicConfig(level=logging.DEBUG, disable_existing_loggers=0)
    main()
