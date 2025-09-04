from typing import Optional, Type
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from utils.models import Configuration
from utils.lib import TypePlatform

async def discord_tax_rate(db: AsyncSession):
	stmt = select(Configuration.value).where(Configuration.name == "discord_tax_rate")
	result = await db.execute(stmt)
	return result.scalar_one_or_none()

async def discord_msg_bonus(db: AsyncSession):
	stmt = select(Configuration.value).where(Configuration.name == "discord_msg_bonus")
	result = await db.execute(stmt)
	return result.scalar_one_or_none()

# get unid using specified platform id
async def unid(model: Type[TypePlatform], platform_id: str, db: AsyncSession) -> Optional[int]:
	stmt = select(model.unid).where(model.platform_id == platform_id)
	result = await db.execute(stmt)
	return result.scalar_one_or_none()

# get a column from specified platform
async def platform_row(model: Type[TypePlatform], platform_id: str, db: AsyncSession) -> Optional[TypePlatform]:
	stmt = select(model).where(model.platform_id == platform_id)
	result = await db.execute(stmt)
	return result.scalar_one_or_none()