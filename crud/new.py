from decimal import Decimal
from typing import Optional, Type, TypeVar
from sqlalchemy.ext.asyncio import AsyncSession
from utils.models import Users, DiscordUsers, MinecraftUsers, Coins, CoinTransfers, Reason
from utils.logger import log

# create a new unid user
async def user(db: AsyncSession) -> Optional[int]:
	try:
		async with db.begin():
			new_user = Users()
			db.add(new_user)
			await db.flush()
			await db.refresh(new_user)
			return new_user.unid
	except Exception:
		log.error("exception at new.user()")
		return None

# create a new platform user (any platform)
T = TypeVar("T", DiscordUsers, MinecraftUsers)
async def platform_user(model: Type[T], platform_id: str, db: AsyncSession) -> Optional[int]:
	try:
		async with db.begin():
			unid = await user(db)
			new_user = model(
				unid=unid,
				platform_id=platform_id
			)
			db.add(new_user)
			await db.flush()
			return unid
	except Exception:
		log.error("exception at new.platform_user")
		return None

async def eval_coin(unid: int, value: Decimal, to_admin: Decimal, db: AsyncSession):
	try:
		async with db.begin():
			# user coin
			new_coin = Coins(unid = unid, value = value)
			db.add(new_coin)
			await db.flush()

			new_coin_trans = CoinTransfers(to_unid = unid, new_coin_id = new_coin.coin_id)
			db.add(new_coin_trans)

			# admin coin
			admin_coin = Coins(unid = 0, value = to_admin)
			db.add(admin_coin)
			await db.flush()

			admin_coin_trans = CoinTransfers(
				source_coin_id = new_coin.coin_id,
				from_unid = unid,
				to_unid = 0,
				new_coin_id = admin_coin.coin_id,
				reason = Reason.EVAL_TAX
			)
			db.add(admin_coin_trans)
	except Exception:
		log.error("exception at new.eval_coin()")
		return None