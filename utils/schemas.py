from pydantic import BaseModel
from typing import Optional
from enum import Enum

class Platform(str, Enum):
	discord = "discord"
	minecraft = "minecraft"

class Eval(BaseModel):
	platform: Platform
	platform_id: str
	message_id: Optional[str] = None
	message_length: str

class EvalResponse(BaseModel):
	success: bool
	reason: str | None = None
	result: int | None = None