from pydantic import BaseModel

class Eval(BaseModel):
	platform_id: str
	message_length: int

class Balance(BaseModel):
	platform_id: str

class Pay(BaseModel):
	sender_platform_id: str
	receiver_platform_id: str
	amount: int

class Response(BaseModel):
	success: bool
	reason: str | None = None
	result: int | None = None