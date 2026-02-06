from sqlalchemy.ext.asyncio import AsyncSession
from collections.abc import Sequence
from sqlalchemy import select
from sqlalchemy import func
from decimal import Decimal
import math

from ..utils.models import Configuration
from ..utils.models import Coins
from ..utils.lib import TypePlatform
from ..utils.lib import UserEval
from .fun import User
from ..utils.logger import log

class Get:

  def __init__(self, user: 'User'):
    self.user = user

  # get balance of a user using unid
  async def balance(self, unid: str = None) -> Decimal:
    if unid: _ = unid
    else: _ = await self.unid()
    stmt = (
      select(func.sum(Coins.value))
      .where(
        Coins.unid == _,
        Coins.spent == False  # noqa: E712
      )
    )
    result = await self.user.db.execute(stmt)
    bal = result.scalar_one_or_none()
    _bal: Decimal = Decimal(bal) if bal is not None else Decimal('0')

    return _bal

  # get the platform row
  async def platform_row(self, platform_id: str = None, lock: bool = False) -> TypePlatform | None:
    _ = self.user.platform_id
    if platform_id is not None: _ = platform_id
    stmt = select(self.user.platform).where(self.user.platform.platform_id == _)
    if lock: stmt = stmt.with_for_update()
    result = await self.user.db.execute(stmt)
    return result.scalar_one_or_none()

  # get if user exists or not in True or None
  async def user_validation(self) -> bool | None:
    _ = await self.platform_row()
    if _: return True
    else: return None

  # get unid of user
  async def unid(self, platform_id: str = None) -> str | None:
    row = await self.platform_row(platform_id if platform_id is not None else self.user.platform_id)
    if row: return str(row.unid)
    return None

  async def userEvalRewardMessage(self, _platform_row: TypePlatform, user_evals: list[UserEval]) -> Decimal:

    last_time: int = int(str(_platform_row.last_message))
    message_count: int = int(str(_platform_row.message_count))
    reward = Decimal("0")
    # message bonus
    message_bonus = await discord_msg_bonus(self.user.db)
    tax_rate = await discord_tax_rate(self.user.db)

    for userEval in user_evals:

      # time gap
      time_gap = userEval.current_time - last_time
      last_time = userEval.current_time


      total_gain = await formulated_value(
        time_gap,
        userEval.message_length,
        message_count,
        message_bonus
      )
      to_user, to_admin = await taxed_formulated_value(total_gain, tax_rate)

      reward = reward + to_user
      message_count += 1

    return reward

  # transaction stuff ##########################################################

  # unspent coin list
  async def unspent_coin_list(self, unid: str = None) -> list[Coins]:

    if unid: _ = unid
    else: _ = await self.unid()

    stmt = (
      select(Coins)
      .where(
        Coins.unid == _,
        Coins.spent == False
      )
    )
    result = await self.user.db.execute(stmt)
    return list(result.scalars().all())

  # coin list to use for a transaction with a specified amount
  @staticmethod
  def transaction_candidates(
    _unspent_coin_list: list[Coins],
    amount: Decimal
  ) -> tuple[list[Coins], Decimal]:

    # sort the coin list from smallest to largest (when doing a transaction we always merge small coins)
    sorted_unspent_coin_list: list[Coins] = sorted(_unspent_coin_list, key=lambda c: c.value)

    selected_coins: list[Coins] = []
    current_sum = Decimal('0')

    # iterate through the sorted coins, adding them until amount if reached
    for coin in sorted_unspent_coin_list:

      selected_coins.append(coin)
      current_sum += coin.value

      if current_sum >= amount:
        # return selected_coins, current_sum
        break

    return selected_coins, current_sum

  # lock coins for transaction
  async def transaction_lock(self, coins_to_lock: list[Coins]) -> Sequence[Coins] | None:

    candidates_ids = [coin.coin_id for coin in coins_to_lock]

    lock_stmt = (
      select(Coins)
      .where(
        Coins.coin_id.in_(candidates_ids)
      )
      .with_for_update(nowait=True)
    )

    lock_result = await self.user.db.execute(lock_stmt)
    locked_coins = lock_result.scalars().all()

    if len(locked_coins) != len(candidates_ids):
      return None

    return locked_coins

# old shit #####################################################################

async def discord_tax_rate(db: AsyncSession) -> Decimal:
  stmt = select(Configuration.value).where(Configuration.name == "discord_tax_rate")
  result = await db.execute(stmt)
  output = result.scalar_one_or_none()
  return output if output is not None else log.error("configuration fetching error")

async def discord_msg_bonus(db: AsyncSession) -> Decimal:
  stmt = select(Configuration.value).where(Configuration.name == "discord_msg_bonus")
  result = await db.execute(stmt)
  output = result.scalar_one_or_none()
  return output if output is not None else log.error("configuration fetching error")

# get unid using specified platform id

# get a column from specified platform
async def platform_row(platform: type[TypePlatform], platform_id: str, lock_row: bool, db: AsyncSession) -> TypePlatform | None:
  stmt = select(platform).where(platform.platform_id == platform_id)
  if lock_row:
    stmt = stmt.with_for_update()
  result = await db.execute(stmt)
  return result.scalar_one_or_none()

## transaction related fun.pay

# helper class for storing selected coins in a transaction
# class CoinSelection:
#
#   def __init__(self, coin_id: int, value: Decimal):
#     self.coin_id: int = coin_id
#     self.value: Decimal = value

  # def __repr__(self):
  # 	return f"CoinSelection(id={self.coin_id}, value={self.value})"

# get unspent coin list of a user using unid
# async def unspent_coin_list(user_unid: str, db: AsyncSession) -> list[CoinSelection]:
#
#   stmt = (
#     select(Coins.coin_id, Coins.value)
#     .where(
#       Coins.unid == user_unid,
#       Coins.spent == False  # noqa: E712
#     )
#   )
#   result = await db.execute(stmt)
#   result2 = result.all()
#   _unspent_coin_list: list[CoinSelection] = [CoinSelection(c[0], c[1]) for c in result2]  # pyright: ignore[reportAny]
#
#   return _unspent_coin_list


async def taxed_formulated_value(total_gain: Decimal, tax_rate: Decimal) -> tuple[Decimal, Decimal]:
  tax_rate_value = total_gain * (Decimal(tax_rate) / Decimal(100))
  gain_after_tax_rate_value = total_gain - tax_rate_value
  to_user = Decimal(math.floor(gain_after_tax_rate_value))
  precision_remainder_to_be_added_to_tax = gain_after_tax_rate_value - Decimal(to_user)
  to_admin = (tax_rate_value + precision_remainder_to_be_added_to_tax).quantize((Decimal("0.01")))
  return to_user, to_admin

async def formulated_value(time_gap: int, msg_length: int, msg_count: int, msg_bonus: Decimal) -> Decimal:

  time_value_float: float = float(time_gap) * 0.15
  if time_value_float > 1:
    # ensure the value inside log is positive
    log_arg = 1 + (float(time_gap) - 7 / 60)

    if log_arg > 0:
      overflow = 1.2 * math.log(log_arg) / math.log(61)
      time_value: Decimal = Decimal(1 + overflow)
    else:
      time_value = Decimal(time_value_float)
  else:
    time_value = Decimal(time_value_float)

  # base total
  total_gain = (
    Decimal(msg_length)
      * (Decimal(1) + msg_bonus * Decimal(msg_count))
      * time_value
  ).quantize(Decimal("0.01"))  # 2 decimal places

  return total_gain
