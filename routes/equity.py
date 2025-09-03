from typing import Annotated
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from utils.db import get_db
from utils.logger import log
from utils import schemas
from crud import funcs

router = APIRouter()
DB = Annotated[Session, Depends(get_db)]

@router.get('/')
def equity():
	return { 'msg': 'equity' }

@router.post('/eval', response_model=schemas.EvalResponse)
def eval(req: schemas.Eval, db: DB):
	return funcs.eval(req, db)

@router.get('/balance')
def balance(req: schemas.Eval) -> int:
	log.debug(f'Received req for {req.id}')
	return 0