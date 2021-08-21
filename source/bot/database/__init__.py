from sqlalchemy.orm import declarative_base, sessionmaker
import sqlalchemy
from bot.secrets.dbSecrets import DRIVER, USER, PASS, HOST, PORT, DATABASE

tableBase = declarative_base()

class DBConn:

    def __init__(self):
        self._base = tableBase
        self._dbUrl = sqlalchemy.engine.URL(drivername=DRIVER, username=USER, password=PASS, host=HOST, port=PORT, database=DATABASE)
        self.engine = sqlalchemy.create_engine(self._dbUrl, pool_pre_ping=True, pool_use_lifo=True)
        self.session = sessionmaker(bind=self.engine, future=True)

        self._base.metadata.create_all(self.engine)

    