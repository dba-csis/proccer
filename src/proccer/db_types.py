'Various SQLAlchemy type decorators.'

import jsonlib as json
from sqlalchemy.types import TypeDecorator, VARCHAR


class JSON(TypeDecorator):
    '''Platform-independt Array-of-strings type.

    Not so independent right now, actually. Need PostgreSQL support.'''

    impl = VARCHAR

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(VARCHAR())

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        else:
            return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            return json.loads(value)
