from pydantic import BaseModel
from pydantic import conint
from typing import Optional

from .lib import Platform

PositiveInt = conint(gt=0)

class Eval(BaseModel):
	platform: Platform
	platform_id: str
	message_id: Optional[str] = None
	message_length: PositiveInt
	debug_timestamp: str | None = None # this is for debugging / simulation

class Balance(BaseModel):
	platform: Platform
	platform_id: str

class Pay(BaseModel):
	platform: Platform
	sender_platform_id: str
	receiver_platform_id: str
	amount: PositiveInt

class Response(BaseModel):
	success: bool
	reason: str | None = None
	result: int | None = None