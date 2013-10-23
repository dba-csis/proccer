from __future__ import with_statement, division
# FIXME - Need to scrap pre 2.7 support, so we can have lovely
# unicode_literals.

from calendar import timegm
from contextlib import contextmanager
from datetime import datetime, timedelta
import jsonlib as json
import logging
import os
import re
from time import strptime

from sqlalchemy import create_engine
from sqlalchemy import Column, ForeignKey
from sqlalchemy import Integer, String, DateTime, Interval
from sqlalchemy.ext.declarative import declarative_base, declared_attr
from sqlalchemy.orm import scoped_session, sessionmaker, relationship
from sqlalchemy.orm.exc import NoResultFound

from proccer.db_types import JSON
from proccer.mail import state_change_notification

log = logging.getLogger(__name__)

# Configure engine and create session class.
database_uri = os.environ.get('DATABASE_URL',
                              'postgresql://proccer@localhost/proccer')
engine = create_engine(database_uri)
Session = scoped_session(sessionmaker(bind=engine))

# Create declarative mappings.
Base = declarative_base()


def populate_database(session):
    session.add_all(JobState(id=id, name=name)
                    for name, id in job_state_id.items())
    session.commit()

job_state_id = {
    'ok': 1,
    'error': 2,
    'late': 3,
}
job_state_name = dict((v, k) for k, v in job_state_id.items())

class JobState(Base):
    __tablename__ = 'proccer_state'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)


state_property = property(
    lambda o: job_state_name[o.state_id] if o.state_id else None,
    lambda o, v: setattr(o, 'state_id', job_state_id[v]))

class Job(Base):
    __tablename__ = 'proccer_job'

    id = Column(Integer, primary_key=True)

    deleted = Column(DateTime, nullable=True)

    host = Column(String, nullable=False)
    login = Column(String, nullable=False)
    name = Column(String, nullable=False)

    # last_seen is the timestamp from the remote host, last_stamp is the
    # timestamp from the local host.
    last_seen = Column(DateTime, nullable=False)
    last_stamp = Column(DateTime, nullable=False)
    state_id = Column('state', Integer, ForeignKey('proccer_state.id'),
                      nullable=False)

    warn_after = Column(Interval, nullable=True)
    notify = Column(JSON, nullable=True)

    state = state_property

    def __unicode__(self):
        return u'%s @ %s / %s' % (self.login,
                                  self.host.split('.')[0],
                                  self.name)

    @classmethod
    def get(cls, session, id):
        return session.query(Job).get(id)

    @classmethod
    def create(cls, session, host, login, name):
        now = datetime.utcnow()
        job = Job(host=host, login=login, name=name)
        session.add(job)
        return job

    @classmethod
    def get_or_create(cls, session, host, login, name):
        try:
            return (session
                        .query(Job)
                        .filter_by(host=host, login=login, name=name)
                        .one())
        except NoResultFound:
            return Job.create(session, host, login, name)

    @property
    def results(self):
        return (Session.object_session(self)
                    .query(JobResult)
                    .filter(JobResult.job_id == self.id)
                    .order_by(JobResult.stamp.desc()))

    @property
    def history(self):
        return (Session.object_session(self)
                    .query(JobHistory)
                    .filter(JobHistory.job_id == self.id)
                    .order_by(JobHistory.started.desc()))


class JobResult(Base):
    __tablename__ = 'proccer_result'

    id = Column(Integer, primary_key=True)

    job_id = Column('job', Integer, ForeignKey('proccer_job.id'),
                    nullable=False)
    job = relationship('Job')
    stamp = Column(DateTime, nullable=False)
    state_id = Column('state', Integer, ForeignKey('proccer_state.id'),
                      nullable=False)
    clock_ms = Column(Integer, nullable=False)
    output = Column(String, nullable=True)
    result = Column(JSON, nullable=False)
    rusage = Column(JSON, nullable=False)

    state = state_property

    @classmethod
    def create(cls, job, clock_ms, result, rusage, output):
        r = JobResult(job=job, state=job.state, clock_ms=clock_ms,
                      result=result, rusage=rusage, output=output,
                      stamp=job.last_seen)
        Session.object_session(job).add(r)
        return r


class JobHistory(Base):
    __tablename__ = 'proccer_history'

    id = Column(Integer, primary_key=True)

    job_id = Column('job', Integer, ForeignKey('proccer_job.id'),
                    nullable=False)
    job = relationship('Job')
    state_id = Column('state', Integer, ForeignKey('proccer_state.id'),
                      nullable=False)
    started = Column(DateTime, nullable=False)
    ended = Column(DateTime, nullable=True)

    state = state_property

    @classmethod
    def create(cls, job):
        history = JobHistory(job=job, started=job.last_seen, state=job.state)
        Session.object_session(job).add(history)
        return history

### FIXME - We're missing the indices.


@contextmanager
def session_manager():
    'Context manager for database-connection setup/teardown.'

    session = Session()
    try:
        yield session
        session.commit()
    finally:
        Session.remove()


def update_proccer_job(session, result):
    'Create or update proccer_job row returning the updated row.'

    stamp = datetime.utcfromtimestamp(timegm(strptime(result['stamp'],
                                                      '%Y-%m-%dT%H:%M:%SZ')))
    new_state = 'ok' if result['result']['ok'] else 'error'

    # Find existing proccer_job
    job = Job.get_or_create(session,
                            host=result['host'],
                            login=result['login'],
                            name=result['name'])
    if job.deleted:
        log.info('Reviving zombie-job %r', job.id)
        job.deleted = None
    job.last_seen = stamp
    old_state, job.state = job.state, new_state

    config = result.get('config', {})
    job.warn_after = parse_interval(config.get('warn-after'))
    job.notify = config.get('notify')

    log.debug('old/new state for job %r: %s/%s',
              job.id, old_state, new_state)

    if old_state != new_state:
        job.last_stamp = datetime.utcnow()
        update_job_history(job)
        job_state_changed(job, result)

    return job


def update_job_history(job):
    if job.history.count():
        previous = job.history.filter(JobHistory.ended == None).one()
        previous.ended = job.last_seen
    JobHistory.create(job)


def job_state_changed(job, result):
    # FIXME - Background job!
    try:
        state_change_notification(job, result)
    except Exception, ex:
        log.error('Could not send state-change notification mail',
                  exc_info=True)


def add_proccer_result(session, job, result):
    'Insert result in proccer_result.'

    JobResult.create(job,
                     clock_ms=int(result['clock'] * 1000),
                     result=result['result'],
                     rusage=result['rusage'],
                     output=result['output'])


intervals = {
    'seconds': 1,
    'minutes': 60,
    'hours': 60 * 60,
    'days': 24 * 60 * 60,
}


def parse_interval(s):
    if s is None:
        return None
    try:
        count, interval = s.split()
        return timedelta(seconds=int(count) * intervals[interval])
    except (KeyError, ValueError):
        raise ValueError('Bad interval', s)
