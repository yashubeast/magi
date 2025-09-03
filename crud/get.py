from typing import Optional, Type, TypeVar
from utils.models import DiscordUsers, MinecraftUsers, Configuration
from sqlalchemy.orm import Session

def discord_tax_rate(db):
	row: Configuration = db.query(Configuration).filter(Configuration.name == "discord_tax_rate").first()
	return row.value

def discord_msg_bonus(db):
	row: Configuration = db.query(Configuration).filter(Configuration.name == "discord_msg_bonus").first()
	return row.value

def unid(model, platform_id: str, db: Session):
	row = db.query(model).filter(model.platform_id == platform_id).first()
	return row.unid if row else None

T = TypeVar("T", DiscordUsers, MinecraftUsers)
def platform_row(model: Type[T], platform_aid: str, db: Session) -> Optional[T]:
	return db.query(model) .filter(model.platform_id == platform_aid) .first()