from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from typing import Generic
import time

from .. import DiscordUsers
from ..utils.models import TransactionLinkReason
from ..utils.models import TransactionReason
from ..utils.models import TransactionLinks
from ..utils.models import Transactions
from ..utils.models import Coins
from ..utils.lib import PlatformAcitivities
from ..utils.lib import PlatformToEnumLink
from ..utils.lib import PayoutQueueLock
from ..utils.lib import TypePlatform
from ..utils.lib import PayoutQueue
from ..utils.lib import UserEval
from ..utils.logger import log
from ..utils import schemas

class User(Generic[TypePlatform]):

  def __init__(
    self,
    platform: type[TypePlatform],
    platform_id: str,
    db: AsyncSession,
  ):
    self.platform = platform
    self.platform_id = platform_id
    self.db = db

    from .get import Get
    from .new import New
    self.get = Get(self)
    self.new = New(self)

  async def evalMessage(self, message_length: int) -> schemas.Response:
    
    if message_length < 1: return schemas.Response(success=False, reason="invalid message length")
    elif message_length > 500: message_length = 500

    # user validation
    row = await self.get.user_validation()

    # create new user
    if row is None:
      await self.new.platform_user()
      await self.db.commit()
      # TODO: pay user money cuz uh they're new idk
      return schemas.Response(success=True)

    # schedule evaluation for existing user
    current_time: int = int(time.time())

    userEval = UserEval(current_time, message_length)

    async with PayoutQueueLock:
      PayoutQueue[self.platform][PlatformAcitivities.message][self.platform_id].append(userEval)

    return schemas.Response(success=True)

  async def balance(self) -> schemas.Response:

    # user validation
    row = await self.get.platform_row()
    if row is None: return schemas.Response(success=False, reason='invalid user')
    # balance_in_decimal: Decimal = await get.balance_in_decimal(row.unid, self.db)
    # balance_in_decimal: Decimal = await self._get_balance(str(row.unid))
    balance_in_decimal: Decimal = await self.get.balance(str(row.unid))
    _balance: int = int(balance_in_decimal)
    return schemas.Response(success=True, result=_balance)

  async def pay(self, req: schemas.Pay) -> schemas.Response:

    # handle self transfer, raw using the provided platform ids
    if req.sender_platform_id == req.receiver_platform_id: return schemas.Response(success=False, reason="self transfer not allowed")

    # handle invalid amount, maybe move this to schemas ? idk
    if req.amount < 1: return schemas.Response(success = False, reason = "invalid amount")

    # user validation & get unid
    unid_sender = await self.get.unid()
    if unid_sender is None: return schemas.Response(success=False, reason="invalid sender")
    unid_receiver = await self.get.unid(req.receiver_platform_id)
    if unid_receiver is None: return schemas.Response(success=False, reason="invalid receiver")

    # handle self transfer, again cuz why not, using unid
    # TODO: add a alert if this ever gets triggered, just cuz im curious
    if unid_sender == unid_receiver: return schemas.Response(success=False, reason="self transfer not allowed")

    amount: Decimal = Decimal(req.amount)

    sender_balance: Decimal = await self.get.balance(unid_sender)
    if not sender_balance >= amount: return schemas.Response(success=False, reason="insufficient balance")

    _unspent_coin_list = await self.get.unspent_coin_list(unid_sender)

    # transaction_candidates here CAN return None
    # however it won't here because the sender_balance is always going to be higher than amount
    # meaning there's always enough candidates
    # transaction_candidates: list[CoinSelection], sum_of_candidates = get.transaction_candidates(_unspent_coin_list, amount)
    _tuple: tuple[list[Coins], Decimal] = (
      self.get.transaction_candidates(_unspent_coin_list, amount)
    )
    # still handling it cuz why the fuck not
    if _tuple is None:
      await self.db.rollback()
      return schemas.Response(success=False, reason="trouble finding coins to transfer, enough balance for payment but trouble finding transaction candidates")

    transaction_candidates = _tuple[0]
    sum_of_candidates = _tuple[1]
    return_amount: Decimal = sum_of_candidates - amount

    locked_coins = await self.get.transaction_lock(transaction_candidates)
    if locked_coins is None:
      # await db.rollback()
      # don't need db.rollback() cuz using "nowait=True" while locking the rows
      # the transaction automatically rolls back when leaving the transaction block
      return schemas.Response(
        success=False, reason="trouble locking coins, try again"
      )

    for coin in locked_coins:
      coin.spent = True

    # create transaction
    txn = Transactions(
      reason = TransactionReason.pay,
      platform = PlatformToEnumLink.get_enum_using_class(self.platform),
      transaction_links = []
    )
    self.db.add(txn)

    # give coin to users #######################################################

    # receiver
    txnl_receiver = TransactionLinks(
      type = TransactionLinkReason.output,
      coins = Coins(
        unid = unid_receiver,
        value = amount
      )
    )
    txn.transaction_links.append(txnl_receiver)

    # sender return
    if return_amount >= Decimal("1"):
      txnl_sender_return = TransactionLinks(
        type = TransactionLinkReason.output,
        coins = Coins(
          unid = unid_sender,
          value = return_amount
        )
      )
      txn.transaction_links.append(txnl_sender_return)

    # locked coins
    for coin in locked_coins:
      txnl = TransactionLinks(
        type = TransactionLinkReason.input,
        coin_id = coin.coin_id
      )
      txn.transaction_links.append(txnl)

    await self.db.flush()
    await self.db.commit()
    log.debug(
      f"from[{req.sender_platform_id}] to [{req.receiver_platform_id}] >>> "
      f"amt[{req.amount}] gave[{sum_of_candidates}] return[{return_amount}] "
      f"txid[{txn.txid}] coins[{[int(c.value) for c in transaction_candidates]}]"
    )
    return schemas.Response(
      success=True,
      reason=f"paid: {amount}, gave: {int(sum_of_candidates)}, returned: {int(return_amount)}, txid: #{txn.txid}, coins: {[int(c.value) for c in transaction_candidates]}"
    )

  async def payout(self):

    async with PayoutQueueLock:
      # discord / minecraft
      for platform in PayoutQueue:
        activities = PayoutQueue[platform]
        # message / smth else
        for activity in activities:
          platform_ids = activities[activity]

          # init txn
          # txn = await self.new.transaction(
          #   TransactionReason.genesis_message,
          #   PlatformToEnumLink.get_enum_using_class(platform)
          # )
          txn = Transactions(
            reason = TransactionReason.genesis_message,
            platform = PlatformToEnumLink.get_enum_using_class(platform),
            transaction_links = []
          )

          for platform_id in platform_ids:

            userEvals = platform_ids[platform_id]
            platform_row = await self.get.platform_row(platform_id)

            # update platform row
            platform_row.message_count += len(userEvals)
            platform_row.last_message = userEvals[-1].current_time

            # calculate money
            reward = await self.get.userEvalRewardMessage(
              platform_row,
              userEvals
            )
            if reward < Decimal("1"): continue

            # confirm addition of transaction if atleast 1 user earned money
            if txn not in self.db: self.db.add(txn)

            # pay money
            transaction_link = TransactionLinks(
              type = TransactionLinkReason.output,
              coins = Coins(
                unid = platform_row.unid,
                value = reward
              )
            )
            txn.transaction_links.append(transaction_link)

            log.debug(
              f"{platform.__platform_name__} {activity} >>> "
              f"pid[{platform_id}] amt[{reward}] msgs[{len(userEvals)}]"
            )

      # empty PayoutQueue
      PayoutQueue.clear()

    await self.db.commit()

async def payout(session_factory: async_sessionmaker):

  async with session_factory() as session:
    try:
      user = User(DiscordUsers, "0", session)
      await user.payout()

    except Exception as e:
      await session.rollback()
      log.error(f"payout failed: {e}")