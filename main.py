from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
import uvicorn
import os

from pkg import database
from pkg import default_entries
from pkg import log

from routes import equity

# env stuff
_ = load_dotenv()
PORT = int(os.environ.get("PORT", 8080))
RELOAD = os.environ.get("UVICORN_RELOAD", "True").lower() == "true"

# startup
@asynccontextmanager
async def lifespan(app: FastAPI):  # pyright: ignore[reportUnusedParameter]
	# create tables
	async with database.engine.begin() as db:
		await db.run_sync(database.Base.metadata.create_all)

	# insert default rows
	async with database.AsyncSessionLocal() as session:
		await default_entries(session)

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
		reload = RELOAD
	)
	log.info("running")