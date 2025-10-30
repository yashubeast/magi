from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter
from fastapi import Depends
from typing import Annotated

from pkg import DiscordUsers
from pkg import database
from pkg import schemas
from pkg import fun

router = APIRouter()
DB = Annotated[AsyncSession, Depends(database.get_db)]

@router.get('/')
async def equity():
  return { 'msg': 'equity' }

# discord
@router.post('/discord/eval', response_model=schemas.Response)
async def eval(req: schemas.Eval, db: DB) -> schemas.Response:
  return await fun.eval(req, DiscordUsers, db)

@router.get('/discord/balance', response_model=schemas.Response)
async def balance(req: schemas.Balance, db: DB) -> schemas.Response:
  return await fun.balance(req, DiscordUsers, db)

@router.post('/discord/pay', response_model=schemas.Response)
async def pay(req: schemas.Pay, db: DB) -> schemas.Response:
  return await fun.pay(req, DiscordUsers, db)

# minecraft
# @router.post('/minecraft/eval', response_model=schemas.Response)
# async def eval(req: schemas.Eval, db: DB) -> schemas.Response:
# 	return await fun.eval(req, db)

# @router.get('/minecraft/balance', response_model=schemas.Response)
# async def balance(req: schemas.Balance, db: DB) -> schemas.Response:
# 	return await fun.balance(req, db)

# @router.post('/minecraft/pay', response_model=schemas.Response)
# async def pay(req: schemas.Pay, db: DB) -> schemas.Response:
# 	return await fun.pay(req, db)
