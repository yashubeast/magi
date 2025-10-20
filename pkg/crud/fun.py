import math
import time
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal
from typing import Type
from typing import Optional

from pkg import DiscordUsers
from pkg import schemas

from . import new
from . import get
from pkg import log
from pkg import TypePlatform

async def eval(req: schemas.Eval, db: AsyncSession) -> schemas.Response:

	try:
		async with db.begin():

			# get platform model
			platform: Type[TypePlatform] = await get.platform_model(req.platform)

			# required values
			platform_id: str = req.platform_id
			message_length: str = req.message_length
			current_timestamp: int = int(time.time())
			message_bonus: Decimal = await get.discord_msg_bonus(db)
			tax_rate: Decimal = await get.discord_tax_rate(db)

			# get unid or None
			row: TypePlatform = await get.platform_row(platform, platform_id, db)

			if row is None: # new user
				# new_user = True
				unid = await new.platform_user(platform, platform_id, db)
				time_gap = 10
				message_count = 1
			else:
				unid = row.unid
				# time_gap = current_timestamp - row.last_message
				time_gap = 60 # this is for simulation
				message_count = row.message_count

			log.debug(f"fun.eval: got values: \n"
			          f"> row = {row}\n"
			          f"> platform = {platform}\n"
			          f"> unid = {unid}\n"
			          f"> time_gap = {time_gap}\n"
			          f"> message_length = {message_length}\n"
			          f"> message_count = {message_count}\n"
			          f"> message_bonus = {message_bonus}\n"
			          f"> tax_rate = {tax_rate}")

			#####################################################################################
			# formulation requires time_gap, message_length, message_count, message_bonus, tax_rate

			# time value
			time_value_float: float = float(time_gap) * 0.15
			if time_value_float > 1:
				# ensure the value inside log is positive
				log_arg = 1 + (float(time_gap) - 7 / 60)

				if log_arg > 0:
					overflow = 1.2 * math.log(log_arg) / math.log(61)
					time_value: Decimal = Decimal(1 + overflow)
				else:
					time_value: Decimal = Decimal(time_value_float)
			else:
				time_value: Decimal = Decimal(time_value_float)

			# base total
			total = (
				Decimal(message_length)
				* (Decimal(1) + message_bonus * Decimal(message_count))
				* time_value
			).quantize(Decimal("0.01")) # 2 decimal places

			# tax
			tax_amount = total * (Decimal(tax_rate) / Decimal(100))
			after_tax = total - tax_amount
			total_value = Decimal(math.floor(after_tax))
			remainder = after_tax - Decimal(total_value)
			to_admin = (tax_amount + remainder).quantize(Decimal("0.01"))

			#####################################################################################
			# formulation done, results:
			# total_value - amount which is to be paid to the user
			# to_admin - tax cut off from user gain

			log.debug("fun.eval: finished evaluation: \n"
			          f"> total_value = {total_value}\n"
			          f"> to_admin = {to_admin}")

			# only evaluate when user earns => 1 coins
			if total_value <= 1:
				new_message_count = 0
			else:
				new_message_count = 1

			# update entry
			stmt = (
				update(platform)
				# using and_ here to shut the linter up: every platform object (sql model)
				# used in this function must have a platform_id column
				.where(platform.platform_id == platform_id)
				.values(
					message_count = platform.message_count + new_message_count,
					last_message = current_timestamp
				)
			)
			await db.execute(stmt)
			log.debug("fun.eval: updated platform entry")

			# result here is always going to be 0 and not like 0.77 gain since decimal points are given to miner
			# it can also be in negative when debugging tho, when the time gap is in negative
			if total_value < 1: return schemas.Response(success=False, reason=f"gain below 1", result=int(total_value))

			# give coin
			await new.eval_coin(unid, total_value, to_admin, db)
			log.debug("fun.eval: gave coin")

		return schemas.Response(success=True, result=int(total_value))
	except Exception as e:
		log.debug("exception at fun.eval: ", e)
		return schemas.Response(success=False, reason=f"{e}")

async def balance(req: schemas.Balance, db: AsyncSession) -> schemas.Response:

	try:
		async with db.begin():

			platform: Type[TypePlatform] = await get.platform_model(req.platform)
			unid: Optional[str] = await get.unid(platform, req.platform_id, db)
			if unid is None: return schemas.Response(success=False, reason="invalid user")

			balance_in_decimal: Decimal = await get.balance_in_decimal(unid, db)

			bal: int = int(balance_in_decimal)

		return schemas.Response(success=True, result=bal)
	except Exception as e:
		log.debug("exception at fun.balance: ", e)
		return schemas.Response(success=False, reason=f"{e}")

async def pay(req: schemas.Pay, db: AsyncSession) -> schemas.Response:

	try:
		async with db.begin():

			platform: Type[TypePlatform] = await get.platform_model(req.platform)

			sender_unid: Optional[str] = await get.unid(platform, req.sender_platform_id, db)
			receiver_unid: Optional[str] = await get.unid(platform, req.receiver_platform_id, db)
			if sender_unid is None: return schemas.Response(success=False, reason="invalid sender")
			if receiver_unid is None: return schemas.Response(success=False, reason="invalid receiver")

			amount: Decimal = Decimal(req.amount)

			sender_balance: Decimal = await get.balance_in_decimal(sender_unid, db)
			if not sender_balance >= amount: return schemas.Response(success=False, reason="insufficient balance")

			_unspent_coin_list = await get.unspent_coin_list(sender_unid, db)

			# transaction_candidates here CAN return None
			# however it won't here because the sender_balance is always going to be higher than amount
			# meaning there's always enough candidates
			transaction_candidates, sum_of_candidates = get.transaction_candidates(_unspent_coin_list, amount)
			# still handling it cuz idk
			if transaction_candidates is None:
				await db.rollback()
				return schemas.Response(success=False, reason="trouble finding coins to transfer")

			locked_coins = await get.transaction_lock(transaction_candidates, db)
			if locked_coins is None:
				# await db.rollback()
				# don't need db.rollback() cuz using "nowait=True" while locking the rows
				# the transaction automatically rolls back when leaving the transaction block
				return schemas.Response(success=False, reason="trouble locking coins, try again")

			for coin in locked_coins:
				coin.spent = True

			return_amount: Decimal = sum_of_candidates - amount

			# give coin to users

		return schemas.Response(
			success=True,
			reason=f"coins spent: {[int(c.value) for c in transaction_candidates]} | "
			       f"return amount: {int(return_amount)}"
		)

	except Exception as e:
		log.debug("exception at fun.pay: ", e)
		return schemas.Response(success=False, reason=f"{e}")