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
from ..utils.lib import TP
from ..utils.lib import PayoutQueue
from ..utils.lib import UserEval
from ..utils.lib import Cls
from ..utils.logger import log
from ..utils import schemas

class User(Generic[TP]):

  def __init__(
    self,
    platform: type[TP],
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

  async def transactions(self) -> schemas.Response:

    unid = await self.get.unid()
    txs = await self.get.transactions(unid)

    transaction_list: Cls.TransactionList = []

    # looping transactions
    for tx in txs:

      # TODO: check by debugging first, then fix if the return amount on overpay is being accounted for or not
      # determine type and amount
      sum_input = sum(
        l.coins.value
        for l in tx.transaction_links
        if l.coins.unid == unid
        and l.type.value == "input"
      )
      sum_output = sum(
        l.coins.value
        for l in tx.transaction_links
        if l.coins.unid == unid
        and l.type.value == "output"
      )

      # determine SENT or RECEIVED
      if sum_input > sum_output:
        t_type = Cls.Enums.TransactionListType.sent
        net_amount = sum_input - sum_output
      elif sum_output > sum_input:
        t_type = Cls.Enums.TransactionListType.received
        net_amount = sum_output - sum_input
      else:
        log.error("yo this ain't supposed to happen, check fun.User.transactions")
        continue

      # find the counterparty_id
      # counterparty_id = "if you see this report the bug to yasu for big equity"
      counterparty_id = "idk"
      for link in tx.transaction_links: # looping transaction_links
        # TODO: account for multiple users instead of breaking on first counterparty user
        if link.coins.unid != unid:
          pid = await self.get.platform_id(link.coins.unid)
          if pid:
            counterparty_id = pid
          else:
            counterparty_id = "idk"
          break

      transaction_list.append(Cls.TypedDicts.TransactionListInfo(
        txid = tx.txid,
        amount = int(net_amount),
        counterparty_platform_id = counterparty_id,
        timestamp = tx.timestamp,
        type = t_type
      ))

    return schemas.Response(success = True, transactionList=transaction_list)

  async def payout(self):

    async with PayoutQueueLock:
      for platform in PayoutQueue: # discord / minecraft
        activities = PayoutQueue[platform]

        for activity in activities: # message / smth else
          platform_ids = activities[activity]

          # create a transaction for each unique platform + activity
          txn = Transactions(
            reason = TransactionReason.genesis_message,
            platform = PlatformToEnumLink.get_enum_using_class(platform),
            transaction_links = []
          )

          any_rewards = False

          for platform_id in platform_ids:

            userEvals = platform_ids[platform_id]
            platform_row = await self.get.platform_row(platform_id, platform)
            if platform_row is None:
              log.error("payout function, platform_row doesn't exist")
              continue

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
            any_rewards = True

            # pay money
            coin = Coins(
              unid = platform_row.unid,
              value = reward
            )
            self.db.add(coin)
            transaction_link = TransactionLinks(
              type = TransactionLinkReason.output,
              coins = coin,
              transactions = txn
            )
            log.debug(f"[payout] {transaction_link}")
            txn.transaction_links.append(transaction_link)

            log.debug(
              f"{platform.__platform_name__} {activity} >>> "
              f"pid[{platform_id}] amt[{reward}] msgs[{len(userEvals)}]"
            )

          if any_rewards:
            self.db.add(txn)

      # empty PayoutQueue
      PayoutQueue.clear()

    await self.db.commit()

async def payout(session_factory: async_sessionmaker):

  log.info("payout starting")

  async with session_factory() as session:
    try:
      user = User(DiscordUsers, "0", session)
      await user.payout()

    except Exception as e:
      await session.rollback()
      log.error(f"payout failed: {e}")

    finally:
      log.info("payout finished")
