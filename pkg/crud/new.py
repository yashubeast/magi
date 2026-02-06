from decimal import Decimal

from ..utils.models import TransactionPlatform
from ..utils.models import TransactionReason
from ..utils.models import Transactions
from ..utils.models import Users
from ..utils.models import Coins
from .fun import User

class New:

  def __init__(self, user: 'User'):
    self.user = user

  # new user
  async def unique_user(self) -> str:
    new_user = Users()
    self.user.db.add(new_user)
    await self.user.db.flush()
    return new_user.unid

  # new user in platform
  async def platform_user(self) -> str:
    unid: str = await self.unique_user()
    new_platform_user = self.user.platform(
      unid=unid,
      platform_id=self.user.platform_id
    )
    self.user.db.add(new_platform_user)
    await self.user.db.flush()
    return new_platform_user.unid

  # create a new transaction entry
  # async def transaction(self, reason: TransactionReason, platform: TransactionPlatform) -> Transactions:
  #
  #   new_transaction = Transactions(
  #     reason=reason,
  #     platform=platform,
  #     transaction_links=[]
  #   )
  #   self.user.db.add(new_transaction)
  #   return new_transaction

  # create a new coin
  async def coin(self, unid: str, value: Decimal) -> int:

    new_coin = Coins(unid = unid, value = value)
    self.user.db.add(new_coin)
    await self.user.db.flush()
    return new_coin.coin_id

# old shit #####################################################################

# async def eval_coin(unid: str, value: Decimal, to_admin: Decimal, db: AsyncSession) -> None:
#   try:
#
#     admin_unid = "0000000000000000"
#
#     # create transaction
#     transaction = Transactions(reason = TransactionReason.genesis)
#     db.add(transaction)
#     await db.flush()
#
#     # user coin
#     user_coin = Coins(unid = unid, value = value)
#     db.add(user_coin)
#     await db.flush()
#
#     # admin coin
#     admin_coin = Coins(unid = admin_unid, value = to_admin)
#     db.add(admin_coin)
#     await db.flush()
#
#     transactionLinks = [
#       TransactionLinks(
#         txid = transaction.txid,
#         coin_id = user_coin.coin_id,
#         type = TransactionLinkReason.output
#       ),
#       TransactionLinks(
#         txid = transaction.txid,
#         coin_id = admin_coin.coin_id,
#         type = TransactionLinkReason.output
#       )
#     ]
#     db.add_all(transactionLinks)
#   except Exception as e:
#     log.error("exception at new.eval_coin: ", e)
