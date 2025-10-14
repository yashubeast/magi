from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated

from pkg import database
from pkg import schemas
from pkg import log
from pkg import fun

router = APIRouter()
DB = Annotated[AsyncSession, Depends(database.get_db)]

@router.get('/')
async def equity():
	return { 'msg': 'equity' }

@router.post('/eval', response_model=schemas.Response)
async def eval(req: schemas.Eval, db: DB) -> schemas.Response:
	return await fun.eval(req, db)

@router.get('/balance', response_model=schemas.Response)
async def balance(req: schemas.Balance, db: DB) -> schemas.Response:
	return await fun.balance(req, db)

@router.post('/pay', response_model=schemas.Response)
async def pay(req: schemas.Pay, db: DB) -> schemas.Response:
	return await fun.pay(req, db)
