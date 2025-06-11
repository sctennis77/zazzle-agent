from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from .models import Base
import os

DB_URL = os.getenv('DATABASE_URL', 'sqlite:///zazzle_pipeline.db')

engine = create_engine(DB_URL, echo=False, future=True)

# Enable foreign key support for SQLite
def _fk_pragma_on_connect(dbapi_con, con_record):
    dbapi_con.execute('PRAGMA foreign_keys=ON')

if DB_URL.startswith('sqlite'):
    event.listen(engine, 'connect', _fk_pragma_on_connect)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine) 