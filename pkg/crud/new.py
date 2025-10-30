from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from ..utils.models import TransactionLinkReason
from ..utils.models import TransactionReason
from ..utils.models import TransactionLinks
from ..utils.models import Transactions
from ..utils.lib import TypePlatform
from ..utils.models import Users
from ..utils.models import Coins
from ..utils.logger import log

# create a new unid user
async def user(db: AsyncSession) -> str:

  new_user = Users()
  db.add(new_user)
  await db.flush()
  return new_user.unid

# create a new platform user (any platform)
async def platform_user(platform: type[TypePlatform], platform_id: str, db: AsyncSession) -> str:

  # generate a new unid
  unid: str = await user(db)
  # create a new platform user using unid
  new_user = platform(
    unid=unid,
    platform_id=platform_id
  )
  # add user
  db.add(new_user)
  await db.flush()
  return new_user.unid

async def eval_coin(unid: str, value: Decimal, to_admin: Decimal, db: AsyncSession) -> None:
  try:

    admin_unid = "0000000000000000"

    # create transaction
    transaction = Transactions(reason = TransactionReason.genesis)
    db.add(transaction)
    await db.flush()

    # user coin
    user_coin = Coins(unid = unid, value = value)
    db.add(user_coin)
    await db.flush()

    # admin coin
    admin_coin = Coins(unid = admin_unid, value = to_admin)
    db.add(admin_coin)
    await db.flush()

    transactionLinks = [
      TransactionLinks(
        txid = transaction.txid,
        coin_id = user_coin.coin_id,
        type = TransactionLinkReason.output
      ),
      TransactionLinks(
        txid = transaction.txid,
        coin_id = admin_coin.coin_id,
        type = TransactionLinkReason.output
      )
    ]
    db.add_all(transactionLinks)
  except Exception as e:
    log.error("exception at new.eval_coin: ", e)

async def coin(unid: str, value: Decimal, db: AsyncSession) -> int:

  new_coin = Coins(unid = unid, value = value)
  db.add(new_coin)
  await db.flush()
  return new_coin.coin_id

# create a new transaction
async def transaction(reason: TransactionReason, db: AsyncSession) -> int:

  new_transaction = Transactions(reason=reason)
  db.add(new_transaction)
  await db.flush()
  return new_transaction.txid
