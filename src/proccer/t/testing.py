from __future__ import with_statement

from contextlib import contextmanager
from mock import patch
from sqlalchemy import create_engine
import sys

from proccer import database

__all__ = ['assert_raises', 'assert_eq', 'setup_module', 'setup_hooks']


@contextmanager
def assert_raises(expected_exception):
    '''Context manager for use in tests, where an exception is expected.

    Use like this::

        with assert_raises(Exception):
            raise Exception('I should fail')

    If an instance of :param:`expected_exception` is not raised this will
    raise AssertionError.'''

    try:
        yield
    except expected_exception:
        pass
    else:
        raise AssertionError('%s was not raised'
                             % expected_exception.__name__)


def assert_eq(actual, expected):
    'Assert that two values compare equal.'
    assert actual == expected, '%r not == expected %r' % (actual, expected)


def setup_hooks(module_name):
    '''Setup per-test setup/teardown hooks for all tests in module.

    This is equivalent to decorating each test-function in the module with
    ``@with_setup(setup_function, teardown_function)``.'''

    module = sys.modules[module_name]
    local_setup = getattr(module, 'setup_function', lambda: None)
    local_teardown = getattr(module, 'teardown_function', lambda: None)

    orig_Session = database.Session

    def setup_function():
        engine = create_engine('sqlite://')
        database.Base.metadata.create_all(bind=engine)
        module.session = orig_Session(bind=engine)
        database.populate_database(module.session)
        # Replace database.Session with a MockSession while in testing, to
        # prevent session_manager from dropping our in-memory database too
        # soon.
        database.Session = MockSession(module.session)

        local_setup()

    def teardown_function():
        local_teardown()

        orig_Session.remove()
        database.Session = orig_Session
        module.session = None

    for name, value in module.__dict__.items():
        if name.startswith('test_') and callable(value):
            value.setup = setup_function
            value.teardown = teardown_function


def setup_module(m):
    setup_hooks(m.__name__)


class MockSession(object):
    'I mock the SQLAlchemy Session for tests.'

    def __init__(self, session):
        self.session = session

    def __call__(self):
        return self.session

    def object_session(self, object):
        return self.session.object_session(object)

    def remove(self):
        # No dropping the in-memory database!
        pass
