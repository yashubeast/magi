import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()
DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASS")
SQLALCHEMY_DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@0.0.0.0:3306/magi" # in-memory DB

engine = create_engine(
	SQLALCHEMY_DB_URL,
	pool_pre_ping=True
)

SessionLocal = sessionmaker(
	bind = engine,
	autoflush = False,
	autocommit = False
)

Base = declarative_base()

# dependency for FastAPI routes
def get_db():
	db = SessionLocal()
	try:
		yield db
	finally:
		db.close()