from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI
import uvicorn
import os

from pkg import database
from pkg import default_entries
from pkg import log
from pkg import fun

from routes import equity
from routes import websocket

# env stuff
_ = load_dotenv()
PORT = int(os.environ.get("PORT", 8080))
RELOAD = os.environ.get("UVICORN_RELOAD", "True").lower() == "true"
PAYOUT_INTERVAL = int(os.environ.get("PAYOUT_INTERVAL_IN_SECONDS", 10))

scheduler = AsyncIOScheduler()

# startup
@asynccontextmanager
async def lifespan(_app: FastAPI):

  # create tables
  async with database.engine.begin() as db:
    await db.run_sync(database.Base.metadata.create_all)

    # insert default rows
    async with database.AsyncSessionLocal() as session:
      await default_entries(session)
  
  scheduler.add_job(
    fun.payout,
    trigger=IntervalTrigger(seconds=PAYOUT_INTERVAL),
    id='payout',
    replace_existing=False,
    max_instances=1,
    args=[database.AsyncSessionLocal]
  )
  # start scheduler
  scheduler.start()
  log.info(f"payout initialized with {PAYOUT_INTERVAL}s interval")

  yield # hand over to FastAPI

  if scheduler.running:
    scheduler.shutdown()
    log.info("payout shutting down")

# init
app = FastAPI(lifespan=lifespan)

# include routers
app.include_router(equity.router, prefix = '/equity')
app.include_router(websocket.router, prefix = '/websocket')

# run
if __name__ == "__main__":
  uvicorn.run(
    'main:app',
    host = '0.0.0.0',
    port = PORT,
    reload = RELOAD
  )

# TODO: make cascades on table relations so deleting any user deletes everything that belonged to them
# TODO: payout currently hogs api requests