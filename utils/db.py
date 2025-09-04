import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()
DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASS")
SQLALCHEMY_DB_URL = f"mysql+asyncmy://{DB_USER}:{DB_PASS}@0.0.0.0:3306/magi"

engine = create_async_engine(
	SQLALCHEMY_DB_URL,
	pool_pre_ping=True
)

AsyncSessionLocal = sessionmaker(
	bind = engine,
	class_ = AsyncSession,
	expire_on_commit= False
)

Base = declarative_base()

# dependency for FastAPI routes
async def get_db():
	async with AsyncSessionLocal() as session:
		yield session