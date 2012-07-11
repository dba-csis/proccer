#!/usr/bin/env python

'Apply database-changes scripts.'

from __future__ import with_statement

from datetime import datetime
import os
import sys
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, String, DateTime

from proccer.database import session_manager

here = os.path.dirname(__file__)

# The database migration models
Base = declarative_base()

class AppliedChanges(Base):
    __tablename__ = 'applied_changes'

    applied = Column(DateTime, nullable=False)
    name = Column(String, primary_key=True)


def parse_sql_script(f):
    return filter(None, [s.strip() for s in f.read().strip().split('\n\n')])

def apply_script(session, script):
    with open(script) as file:
        cnx = session.connection()
        if script.endswith('.sql'):
            for statement in parse_sql_script(file):
                cnx.execute(statement)

        elif script.endswith('.py'):
            code = compile(file.read(), script, 'exec')
            eval(code, {'session': session, 'cnx': cnx})

def main(changes):
    really = '-n' not in sys.argv

    with session_manager() as session:
        Base.metadata.create_all(bind=session.bind)

        applied = 0
        for name in sorted(os.listdir(changes)):
            if name.endswith('~'):
                continue
            if session.query(AppliedChanges).get(name):
                continue

            print 'Applying %s . . .' % name
            applied += 1

            if really:
                script = os.path.join(changes, name)
                apply_script(session, script)

            change = AppliedChanges(applied=datetime.utcnow(), name=name)
            session.add(change)
            session.commit()

    if not applied:
        print 'No database-changes is good news!'

if __name__ == '__main__':
    main(os.path.join(os.path.dirname(__file__), 'changes'))
