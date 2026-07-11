import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import CreateSchema
from dotenv import load_dotenv

load_dotenv()

SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(SQLALCHEMY_DATABASE_URL, pool_size=20, max_overflow=50, pool_timeout=60.0)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Ensure schema "seguridad" is created before tables
event.listen(Base.metadata, 'before_create', CreateSchema('seguridad', if_not_exists=True))

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

