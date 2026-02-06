from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter
from fastapi import WebSocket
from fastapi import Depends
from typing import Annotated
import json

from pkg import DiscordUsers
from pkg import database
from pkg import schemas
from pkg import fun
from pkg.utils.lib import PayoutQueue

router = APIRouter()
DB = Annotated[AsyncSession, Depends(database.get_db)]
active_connections: list[WebSocket] = []

@router.get('/')
async def websocket():
  # await websocket.accept()
  # active_connections.append(websocket)

  return PayoutQueue
  # await websocket.send_text(json.dumps(payload))
  #
  # try:
  #   while True:
  #     await websocket.receive_text()
  # except Exception:
  #   pass
  # finally:
  #   if websocket in active_connections:
  #     active_connections.remove(websocket)
