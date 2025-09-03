import uvicorn, os
from fastapi import FastAPI
from utils.db import Base, engine, SessionLocal
from routes import equity
from utils.lib import default_rows
from dotenv import load_dotenv

# env stuff
load_dotenv()
PORT = int(os.environ.get("PORT", 8080))

# create tables
Base.metadata.create_all(bind=engine)
with SessionLocal() as db: default_rows(db)
# init
app = FastAPI()

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