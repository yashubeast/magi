import math
import time
from decimal import Decimal
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from utils import schemas
from crud import get, new
from utils.models import MinecraftUsers, DiscordUsers, DiscordMsgLogs
from utils.logger import log
from typing import Type, Optional

async def eval(req: schemas.Eval, db: AsyncSession) -> schemas.EvalResponse:

	try:
		async with db.begin():
			# message_id is required for specific platforms (just discord for now)
			match req.platform:
				case schemas.Platform.discord:
					platform: Type[DiscordUsers] = DiscordUsers
					if not req.message_id: return schemas.EvalResponse(success=False, reason="message_id not provided")
				case schemas.Platform.minecraft:
					platform: Type[MinecraftUsers] = MinecraftUsers

			# required values
			platform_id = req.platform_id
			message_length = req.message_length
			current_timestamp = time.time()
			message_bonus = await get.discord_msg_bonus(db)
			tax_rate = await get.discord_tax_rate(db)

			# get unid or None
			row: Optional[DiscordUsers | MinecraftUsers] = await get.platform_row(platform, platform_id, db)

			if not row: # new user
				new_user = True
				unid = await new.platform_user(platform, platform_id, db)
				time_gap = 10
				message_count = 1
			else:
				unid = row.unid
				time_gap = current_timestamp - row.last_message
				message_count = row.message_count

			#####################################################################################
			# formulate requires time_gap, message_length, message_count, message_bonus, tax_rate

			# time value
			time_value = time_gap * 0.15
			if time_value > 1:
				overflow = 1.2 * math.log(1 + (time_gap - 7 / 60)) / math.log(61)
				time_value = 1 + overflow

			# base total
			total = (
			Decimal(message_length)
			* (1 + message_bonus * message_count)
			* Decimal(time_value)
			).quantize(Decimal("0.01")) # 2 decimal places

			# tax
			tax_amount = total * (Decimal(tax_rate) / Decimal(100))
			after_tax = total - tax_amount
			total_value = int(math.floor(after_tax))
			remainder = after_tax - Decimal(total_value)
			to_admin = (tax_amount + remainder).quantize(Decimal("0.01"))

			#####################################################################################
			# formulate done

			# only evaluate when user earns => 1 coins
			if total_value < 1: return schemas.EvalResponse(success=False, reason=f"gain below 1", result=total_value)

			# update entry
			stmt = (
				update(platform)
				.where(platform.platform_id == platform_id)
				.values(
					message_count = platform.message_count + 1,
					last_message = current_timestamp
				)
			)
			await db.execute(stmt)

			# log message if discord
			if req.platform == schemas.Platform.discord:
				msg_log = DiscordMsgLogs(
					discord_id = platform_id,
					message_id = req.message_id,
					value = total_value,
					timestamp = current_timestamp,
				)
				db.add(msg_log)

			# give coin
			await new.eval_coin(unid, total_value, to_admin, db)

			return schemas.EvalResponse(success=True, result=total_value)
	except Exception as e:
		log.exception("exception at fun.eval")
		return schemas.EvalResponse(success=False, reason=f"{e}")