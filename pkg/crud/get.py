from sqlalchemy.ext.asyncio import AsyncSession
from collections.abc import Sequence
from sqlalchemy import select
from sqlalchemy import func
from decimal import Decimal

from ..utils.models import Configuration
from ..utils.models import Coins
from ..utils.lib import TypePlatform

async def discord_tax_rate(db: AsyncSession) -> Decimal:
  stmt = select(Configuration.value).where(Configuration.name == "discord_tax_rate")
  result = await db.execute(stmt)
  output = result.scalar_one_or_none()
  return output if output is not None else Decimal('95.00')

async def discord_msg_bonus(db: AsyncSession) -> Decimal:
  stmt = select(Configuration.value).where(Configuration.name == "discord_msg_bonus")
  result = await db.execute(stmt)
  output = result.scalar_one_or_none()
  return output if output is not None else Decimal('0.00100')

# get unid using specified platform id
async def unid(platform: type[TypePlatform], platform_id: str, db: AsyncSession) -> str | None:
  stmt = select(platform.unid).where(platform.platform_id == platform_id)
  result = await db.execute(stmt)
  return result.scalar_one_or_none()

# get a column from specified platform
async def platform_row(platform: type[TypePlatform], platform_id: str, lock_row: bool, db: AsyncSession) -> TypePlatform | None:
  stmt = select(platform).where(platform.platform_id == platform_id)
  if lock_row:
    stmt = stmt.with_for_update()
  result = await db.execute(stmt)
  return result.scalar_one_or_none()

# get balance in decimal using unid
async def balance_in_decimal(user_unid: str, db: AsyncSession) -> Decimal:

  stmt = (
    select(func.sum(Coins.value))
    .where(
      Coins.unid == user_unid,
      Coins.spent == False  # noqa: E712
    )
  )
  result = await db.execute(stmt)
  bal = result.scalar_one_or_none()
  _bal: Decimal = Decimal(bal) if bal is not None else Decimal('0')

  return _bal

## transaction related fun.pay

# helper class for storing selected coins in a transaction
class CoinSelection:

  def __init__(self, coin_id: int, value: Decimal):
    self.coin_id: int = coin_id
    self.value: Decimal = value

  # def __repr__(self):
  # 	return f"CoinSelection(id={self.coin_id}, value={self.value})"

# get unspent coin list of a user using unid
async def unspent_coin_list(user_unid: str, db: AsyncSession) -> list[CoinSelection]:

  stmt = (
    select(Coins.coin_id, Coins.value)
    .where(
      Coins.unid == user_unid,
      Coins.spent == False  # noqa: E712
    )
  )
  result = await db.execute(stmt)
  result2 = result.all()
  _unspent_coin_list: list[CoinSelection] = [CoinSelection(c[0], c[1]) for c in result2]  # pyright: ignore[reportAny]

  return _unspent_coin_list

# coin list to use for a transaction with a specified amount
def transaction_candidates(
  _unspent_coin_list: list[CoinSelection],
  amount: Decimal
) -> tuple[list[CoinSelection], Decimal] | None:

  # sort the coin list from smallest to largest (when doing a transaction we always merge small coins)
  sorted_unspent_coin_list: list[CoinSelection] = sorted(_unspent_coin_list, key=lambda c: c.value)

  selected_coins: list[CoinSelection] = []
  current_sum = Decimal('0')

  # iterate through the sorted coins, adding them until amount if reached
  for coin in sorted_unspent_coin_list:

    selected_coins.append(coin)
    current_sum += coin.value

    if current_sum >= amount:
      return selected_coins, current_sum

  if current_sum < amount:
    return None

# lock coins for transaction
async def transaction_lock(coins_to_lock: list[CoinSelection], db: AsyncSession) -> Sequence[Coins] | None:

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
