from fastapi import APIRouter

from pkg import DiscordUsers
from pkg import database
from pkg import schemas
from pkg import fun

router = APIRouter()
DB = database.DB

@router.get('/')
async def equity():
  return { 'msg': 'equity' }

# discord
@router.post('/discord/eval', response_model=schemas.Response)
async def discord_eval(req: schemas.Eval, db: DB) -> schemas.Response:
  user = fun.User(DiscordUsers, req.platform_id, db)
  return await user.evalMessage(req.message_length)

@router.get('/discord/balance', response_model=schemas.Response)
async def balance(req: schemas.Balance, db: DB) -> schemas.Response:
  user = fun.User(DiscordUsers, req.platform_id, db)
  return await user.balance()

@router.post('/discord/pay', response_model=schemas.Response)
async def pay(req: schemas.Pay, db: DB) -> schemas.Response:
  user = fun.User(DiscordUsers, req.sender_platform_id, db)
  return await user.pay(req)

# minecraft
# @router.post('/minecraft/eval', response_model=schemas.Response)
# async def minecraft_eval(req: schemas.Eval, db: DB) -> schemas.Response:
# 	return await fun.eval(req, MinecraftUsers, db)

# @router.get('/minecraft/balance', response_model=schemas.Response)
# async def balance(req: schemas.Balance, db: DB) -> schemas.Response:
# 	return await fun.balance(req, db)

# @router.post('/minecraft/pay', response_model=schemas.Response)
# async def pay(req: schemas.Pay, db: DB) -> schemas.Response:
# 	return await fun.pay(req, db)
