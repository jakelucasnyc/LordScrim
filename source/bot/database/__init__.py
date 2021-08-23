from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import sqlalchemy
from bot.secrets.dbSecrets import DRIVER, USER, PASS, HOST, PORT, DATABASE
import logging

tableBase = declarative_base()

class DBConn:

    def __init__(self):
        self._base = tableBase
        self._dbUrl = sqlalchemy.engine.URL(drivername=DRIVER, username=USER, password=PASS, host=HOST, port=PORT, database=DATABASE)
        self.engine = sqlalchemy.create_engine(self._dbUrl)
        self.session = sessionmaker(bind=self.engine, future=True)
        self._logger = logging.getLogger('sqlalchemy.engine')
        self._logger.setLevel(logging.INFO)

        self._base.metadata.create_all(self.engine)

    