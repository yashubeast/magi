from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv
import os

_ = load_dotenv()
DB_HOST = os.environ.get("DB_HOST", "127.0.0.1")
DB_PORT = os.environ.get("DB_PORT", "3306")
DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASS")
SQLALCHEMY_DB_URL = f"mysql+asyncmy://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/equity"

engine = create_async_engine(
  SQLALCHEMY_DB_URL,
  pool_pre_ping=True
)

AsyncSessionLocal = async_sessionmaker(
  bind = engine,
  class_ = AsyncSession,
  expire_on_commit= False
)

class Base(DeclarativeBase):
  pass

# dependency for FastAPI routes
async def get_db():
  async with AsyncSessionLocal() as session:
    yield session
