from typing import TypeVar, Optional
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession
from utils.models import Configuration, DiscordUsers, MinecraftUsers

TypePlatform = TypeVar("TypePlatform", DiscordUsers, MinecraftUsers)

async def default_rows(db: AsyncSession):
	# wacky way to set sudo account in users table
	await db.execute(text("SET SESSION sql_mode = CONCAT_WS(',', @@sql_mode, 'NO_AUTO_VALUE_ON_ZERO')"))
	await db.execute(text("INSERT IGNORE INTO users (unid) VALUES (0)"))

	# default configuration values
	result = await db.execute(select(Configuration))
	config_exists = result.scalars().first()
	if not config_exists:
		db.add_all([
			Configuration(name="discord_tax_rate", value=5.5),
			Configuration(name="discord_msg_bonus", value=0.001),
		])
	await db.commit()