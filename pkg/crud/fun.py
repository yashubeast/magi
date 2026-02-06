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

# more imports are in functions

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
    # pay
    # self.receiver_platform_id = receiver_platform_id
    # self.amount = amount

    from .get import Get
    from .new import New
    self.get = Get(self)
    self.new = New(self)

  ##############################################################################

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

  ##############################################################################

  async def balance(self) -> schemas.Response:

    # user validation
    row = await self.get.platform_row()
    if row is None: return schemas.Response(success=False, reason='invalid user')
    # balance_in_decimal: Decimal = await get.balance_in_decimal(row.unid, self.db)
    # balance_in_decimal: Decimal = await self._get_balance(str(row.unid))
    balance_in_decimal: Decimal = await self.get.balance(str(row.unid))
    _balance: int = int(balance_in_decimal)
    return schemas.Response(success=True, result=_balance)

  ##############################################################################

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

################################################################################

async def payout(session_factory: async_sessionmaker):

  async with session_factory() as session:
    try:
      user = User(DiscordUsers, "0", session)
      await user.payout()

    except Exception as e:
      await session.rollback()
      log.error(f"payout failed: {e}")


















# async def eval(
#   req: schemas.Eval,
#   platform: type[TypePlatform],
#   db: AsyncSession
# ) -> schemas.Response:
#
#   from . import new
#   from . import get
#
#   max_retries_eval: int = 3
#
#   for attempt in range(max_retries_eval):
#     try:
#       async with db.begin():
#
#         # required values
#         platform_id: str = req.platform_id
#         message_length: int = req.message_length
#         current_timestamp: int = int(time.time())
#         message_bonus: Decimal | None = await get.discord_msg_bonus(db)
#         tax_rate: Decimal | None = await get.discord_tax_rate(db)
#
#         row: TypePlatform | None = await get.platform_row(platform, platform_id, True, db)
#
#         if row is None: # new user
#           unid: str = await new.platform_user(platform, platform_id, db)
#           time_gap: int = 10
#           message_count: int = 1
#         else: # existing user
#           unid = row.unid
#           # time_gap = current_timestamp - row.last_message
#           time_gap = 60 # this is for simulation
#           message_count = row.message_count
#
#         log.debug(
#           f"fun.eval: got values: \n"
#           f"> row = {row}\n"
#           f"> platform = {platform}\n"
#           f"> unid = {unid}\n"
#           f"> time_gap = {time_gap}\n"
#           f"> message_length = {message_length}\n"
#           f"> message_count = {message_count}\n"
#           f"> message_bonus = {message_bonus}\n"
#           f"> tax_rate = {tax_rate}"
#         )
#
#         # mathematical part
#         total_gain = await get.formulated_value(time_gap, message_length, message_count, message_bonus)
#         to_user, to_admin = await get.taxed_formulated_value(total_gain, tax_rate)
#
#         log.debug(
#           "fun.eval: finished evaluation: \n"  # pyright: ignore[reportImplicitStringConcatenation]
#           f"> to_user = {to_user}\n"
#           f"> to_admin = {to_admin}"
#         )
#
#         # only evaluate when user earns >= 1 coins
#         new_message_count = 1 if to_user >= 1 else 0
#
#         # update row with new vals
#         if row is not None:
#           row.message_count += new_message_count
#
#           # row.last_message = current_timestamp
#           row.last_message = row.last_message + 60 # this is for simulation
#
#         # result here is always going to be 0 and not like 0.77 gain since decimal points are given to miner
#         # it can also be in negative when debugging tho, when the time gap is in negative
#         if to_user < 1:
#           return schemas.Response(
#             success=False, reason="gain below 1", result=int(to_user)
#           )
#
#         # give coin
#         await new.eval_coin(unid, to_user, to_admin, db)
#         log.debug("fun.eval: gave coin")
#
#       return schemas.Response(success=True, result=int(to_user))
#
#     except Exception as e:
#
#       await db.rollback()
#
#       if "Record has changed" in str(e) and attempt < max_retries_eval - 1:
#         log.debug("reattempting")
#         continue
#       else:
#         log.debug("exception at fun.eval: ", e)
#         return schemas.Response(success=False, reason=f"{e}")
#
#   return schemas.Response(success=False, reason="failed 3 attempts")
#
#
# async def balance(req: schemas.Balance, platform: type[TypePlatform], db: AsyncSession) -> schemas.Response:
#
#   from . import get
#
#   try:
#     async with db.begin():
#       unid: str | None = await get.unid(platform, req.platform_id, db)
#
#       if unid is None:
#         return schemas.Response(success=False, reason='invalid user')
#
#       balance_in_decimal: Decimal = await get.balance_in_decimal(unid, db)
#
#       bal: int = int(balance_in_decimal)
#
#     return schemas.Response(success=True, result=bal)
#
#   except Exception as e:
#     log.debug('exception at fun.balance: ', e)
#     return schemas.Response(success=False, reason=f"{e}")

# async def pay(
#   req: schemas.Pay,
#   platform: type[TypePlatform],
#   db: AsyncSession
# ) -> schemas.Response:
#
#   from . import get
#   from . import new
#
#   try:
#     async with db.begin():
#
#       # handle self transfer, not doing it right now because i keep getting fucking inconsistent use of indentation IM GONNA KILL MYSELF
#       if req.sender_platform_id == req.receiver_platform_id: return schemas.Response(success=False, reason="self transfer not allowed")
#
#       sender_unid: str | None = await get.unid(
#         platform, req.sender_platform_id, db
#       )
#       receiver_unid: str | None = await get.unid(
#         platform, req.receiver_platform_id, db
#       )
#       if sender_unid is None: return schemas.Response(success=False, reason="invalid sender")
#       if receiver_unid is None: return schemas.Response(success=False, reason="invalid receiver")
#       if sender_unid == receiver_unid: return schemas.Response(success=False, reason="self transfer not allowed")
#
#       amount: Decimal = Decimal(req.amount)
#
#       sender_balance: Decimal = await get.balance_in_decimal(sender_unid, db)
#       if not sender_balance >= amount: return schemas.Response(success=False, reason="insufficient balance")
#
#       _unspent_coin_list = await get.unspent_coin_list(sender_unid, db)
#
#       # transaction_candidates here CAN return None
#       # however it won't here because the sender_balance is always going to be higher than amount
#       # meaning there's always enough candidates
#       # transaction_candidates: list[CoinSelection], sum_of_candidates = get.transaction_candidates(_unspent_coin_list, amount)
#       _tuple: tuple[list[get.CoinSelection], Decimal] | None = (
#         get.transaction_candidates(_unspent_coin_list, amount)
#       )
#       # still handling it cuz why the fuck not
#       if _tuple is None:
#         await db.rollback()
#         return schemas.Response(success=False, reason="trouble finding coins to transfer")
#
#       transaction_candidates = _tuple[0]
#       sum_of_candidates = _tuple[1]
#       return_amount: Decimal = sum_of_candidates - amount
#
#       locked_coins = await get.transaction_lock(transaction_candidates, db)
#       if locked_coins is None:
#         # await db.rollback()
#         # don't need db.rollback() cuz using "nowait=True" while locking the rows
#         # the transaction automatically rolls back when leaving the transaction block
#         return schemas.Response(
#           success=False, reason="trouble locking coins, try again"
#         )
#
#       for coin in locked_coins:
#         coin.spent = True
#
#       txid: int = await new.transaction(TransactionReason.pay, db)
#
#       # give coin to users
#
#       receiver_coin: int = await new.coin(receiver_unid, amount, db)
#       sender_coin: int | None = (
#         await new.coin(sender_unid, return_amount, db)
#         if return_amount >= Decimal("1")
#         else None
#       )
#
#       # make transaction links
#       transaction_links: list[dict[str, int | TransactionLinkReason]] = []
#
#       # locked coins
#       for coin in locked_coins:
#         transaction_links.append(
#           {
#             "txid": txid,
#             "coin_id": coin.coin_id,
#             "type": TransactionLinkReason.input,
#           }
#         )
#
#         transaction_links.append(
#           {
#             "txid": txid,
#             "coin_id": receiver_coin,
#             "type": TransactionLinkReason.output,
#           }
#         )
#
#         if sender_coin is not None:
#           transaction_links.append(
#             {
#               "txid": txid,
#               "coin_id": sender_coin,
#               "type": TransactionLinkReason.output,
#             }
#           )
#
#       stmt = insert(TransactionLinks)
#       _ = await db.execute(stmt, transaction_links)
#
#     return schemas.Response(
#       success=True,
#       reason=f"paid: {amount}, gave: {int(sum_of_candidates)}, returned: {int(return_amount)}, txid: #{txid}, coins: {[int(c.value) for c in transaction_candidates]}"
#     )
#
#   except Exception as e:
#     log.debug("exception at fun.pay: ", e)
#     return schemas.Response(success=False, reason=f"{e}")
#
