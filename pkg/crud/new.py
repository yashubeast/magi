from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from typing import Type

from pkg import Users
from pkg import Coins
from pkg import Transactions
from pkg import TransactionLinks
from pkg import TransactionReason
from pkg import TransactionLinkReason
from pkg import log
from pkg import TypePlatform

# create a new unid user
async def user(db: AsyncSession) -> str | None:
	try:
		new_user = Users()
		db.add(new_user)
		await db.flush()
		return new_user.unid
	except Exception as e:
		log.error("exception at new.user: ", e)

# create a new platform user (any platform)
async def platform_user(model: Type[TypePlatform], platform_id: str, db: AsyncSession) -> str | None:
	try:
		# generate a new unid
		unid: str = await user(db)
		# create a new platform user using unid
		new_user = model(
			unid=unid,
			platform_id=platform_id
		)
		# add user
		db.add(new_user)
		await db.flush()
		return unid
	except Exception as e:
		log.error("exception at new.platform_user: ", e)

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

async def coin(unid: str, value: Decimal, db: AsyncSession) -> None:
	try:

		# user coin
		new_coin = Coins(unid = unid, value = value)
		db.add(new_coin)
		await db.flush()

		new_coin_trans = CoinTransfers(to_unid = unid, new_coin_id = new_coin.coin_id)
		db.add(new_coin_trans)

		# admin coin
		admin_coin = Coins(unid = admin_unid, value = to_admin)
		db.add(admin_coin)
		await db.flush()

		admin_coin_trans = CoinTransfers(
			source_coin_id = new_coin.coin_id,
			from_unid = unid,
			to_unid = admin_unid,
			new_coin_id = admin_coin.coin_id,
			reason = CoinTransferReason.EVAL_TAX
		)
		db.add(admin_coin_trans)
	except Exception as e:
		log.error("exception at new.eval_coin: ", e)
