from contextlib import asynccontextmanager

import uvicorn, os
from fastapi import FastAPI
from utils.db import Base, engine, AsyncSessionLocal
from routes import equity
from utils.lib import default_rows
from dotenv import load_dotenv

# env stuff
load_dotenv()
PORT = int(os.environ.get("PORT", 8080))

# startup
@asynccontextmanager
async def lifespan(app: FastAPI):
	# create tables
	async with engine.begin() as db:
		await db.run_sync(Base.metadata.create_all)

	# insert default rows
	async with AsyncSessionLocal() as session:
		await default_rows(session)

	yield # hand over to FastAPI

# init
app = FastAPI(lifespan=lifespan)

# include routers
app.include_router(equity.router, prefix = '/equity')

# run
if __name__ == "__main__":
	uvicorn.run(
		'main:app',
		host = '0.0.0.0',
		port = PORT,
		reload = True
	)