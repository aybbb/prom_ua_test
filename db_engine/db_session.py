from logging import Logger, INFO

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.orm.exc import MultipleResultsFound, NoResultFound

from .db_models import *


class DBSession(scoped_session):

    def __init__(self, user, password, db_host, db_name,
                 logger_name, need_echo=False):
        """Create db session. Return engine and Base class.

            :param user:
                db username;
            :param password:
                db user password;
            :param db_host:
                db host;
            :param db_name:
                db name;
            :param need_echo:
                flag: show or not sql statement.

        """

        self.base = Base
        engine = "postgresql+psycopg2://{user}:{password}@{db_host}/{db_name}"
        engine = engine.format(**vars())
        self.engine = create_engine(engine, convert_unicode=True,
                                    echo=need_echo)
        self.base.metadata.create_all(self.engine)
        maker = sessionmaker(autocommit=False, autoflush=False,
                             bind=self.engine)

        self.logger = Logger(logger_name, level=INFO)

        super().__init__(maker)

    def __call__(self, **kw):
        """Redefine __call__ in sql alchemy to add get_one_or_log function."""

        registry = super().__call__(**kw)
        registry.get_one_or_log = self.get_one_or_log

        return registry

    def get_one_or_log(self, query, message, need_log=True):
        """Get one data from db or write error to log file.

            :param query:
                sql_alchemy query object;
            :param message:
                text or error message which must write to log;
            :param need_log:
                flag to write to log file or not.

        """

        result = None

        # get one result
        try:
            result = query.one()

        # many object returned
        except MultipleResultsFound:
            if need_log:
                msg = "It is a lot of identical {0}.".format(message)
                self.logger.error(msg)

        # no object returned
        except NoResultFound:
            if need_log:
                msg = "Such {0} doesn't exist.".format(message)
                self.logger.error(msg)

        return result