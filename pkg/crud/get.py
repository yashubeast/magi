from sqlalchemy import select
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from typing import Type
from typing import List
from typing import Tuple
from decimal import Decimal

from pkg import TypePlatform
from pkg import Configuration
from pkg import Platform
from pkg import PlatformModel
from pkg import Coins

async def discord_tax_rate(db: AsyncSession) -> Optional[Decimal]:
	stmt = select(Configuration.value).where(Configuration.name == "discord_tax_rate")
	result = await db.execute(stmt)
	return result.scalar_one_or_none()

async def discord_msg_bonus(db: AsyncSession) -> Optional[Decimal]:
	stmt = select(Configuration.value).where(Configuration.name == "discord_msg_bonus")
	result = await db.execute(stmt)
	return result.scalar_one_or_none()

# get unid using specified platform id
async def unid(model: Type[TypePlatform], platform_id: str, db: AsyncSession) -> Optional[str]:
	stmt = select(model.unid).where(model.platform_id == platform_id)
	result = await db.execute(stmt)
	return result.scalar_one_or_none()

# get a column from specified platform
async def platform_row(model: Type[TypePlatform], platform_id: str, db: AsyncSession) -> Optional[TypePlatform]:
	stmt = select(model).where(model.platform_id == platform_id)
	result = await db.execute(stmt)
	return result.scalar_one_or_none()

# get platform table object from platform enum
async def platform_model(platform: Platform) -> Type[TypePlatform]:
	platform: Type[TypePlatform] = PlatformModel.get(platform)
	return platform

# get balance in decimal using unid
async def balance_in_decimal(user_unid: str, db: AsyncSession) -> Decimal:

	stmt = (
		select(func.sum(Coins.value))
		.where(
			Coins.unid == user_unid,
			Coins.spent == False
		)
	)
	result = await db.execute(stmt)
	bal = result.scalar_one_or_none()
	bal: Decimal = Decimal(bal) if bal is not None else Decimal('0')

	return bal

## transaction related fun.pay

# helper class for storing selected coins in a transaction
class CoinSelection:

	def __init__(self, coin_id: int, value: Decimal):
		self.coin_id: int = coin_id
		self.value: Decimal = value

	def __repr__(self):
		return f"CoinSelection(id={self.coin_id}, value={self.value})"

# get unspent coin list of a user using unid
async def unspent_coin_list(user_unid: str, db: AsyncSession) -> List[CoinSelection]:

	stmt = (
		select(Coins.coin_id, Coins.value)
		.where(
			Coins.unid == user_unid,
			Coins.spent == False
		)
	)
	result = await db.execute(stmt)
	_unspent_coin_list: List[CoinSelection] = [CoinSelection(c.coin_id, c.value) for c in result.all()]

	return _unspent_coin_list

# coin list to use for a transaction with a specified amount
def transaction_candidates(
	_unspent_coin_list: List[CoinSelection],
	amount: Decimal
) -> Optional[Tuple[List[CoinSelection], Decimal]]:

	# sort the coin list from smallest to largest (when doing a transaction we always merge small coins)
	sorted_unspent_coin_list: List[CoinSelection] = sorted(_unspent_coin_list, key=lambda c: c.value)

	selected_coins: List[CoinSelection] = []
	current_sum = Decimal('0')

	# iterate through the sorted coins, adding them until amount if reached
	for coin in sorted_unspent_coin_list:

		selected_coins.append(coin)
		current_sum += coin.value

		if current_sum >= amount:
			return selected_coins, current_sum

	if current_sum < amount:
		return None
	else: return selected_coins, current_sum # unreachable but linter is a bitch

# lock coins for transaction
async def transaction_lock(coins_to_lock: List[CoinSelection], db: AsyncSession) -> Optional[List["Coins"]]:

	candidates_ids = [coin.coin_id for coin in coins_to_lock]

	lock_stmt = (
		select(Coins)
		.where(
			Coins.coin_id.in_(candidates_ids)
		)
		.with_for_update(nowait=True)
	)

	lock_result = await db.execute(lock_stmt)
	locked_coins = lock_result.scalars().all()

	if len(locked_coins) != len(candidates_ids):
		return None

	return locked_coins