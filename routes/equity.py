from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from utils.db import get_db
from utils.logger import log
from utils import schemas
from crud import fun

router = APIRouter()
DB = Annotated[AsyncSession, Depends(get_db)]

@router.get('/')
async def equity():
	return { 'msg': 'equity' }

@router.post('/eval', response_model=schemas.EvalResponse)
async def eval(req: schemas.Eval, db: DB):
	return await funcs.eval(req, db)

@router.get('/balance')
async def balance(req: schemas.Eval) -> int:
	log.debug(f'Received req for {req.id}')
	return 0