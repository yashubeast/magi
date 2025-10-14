from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Union
from typing import Final
from typing import Type
from enum import Enum

from .models import Users
from .models import Configuration
from .models import DiscordUsers
from .models import MinecraftUsers
from .logger import log

async def default_entries(db: AsyncSession):

	admin_created = False
	configuration_created = False

	# default admin account
	admin_unid = "0000000000000000"
	# select admin
	admin_result = await db.execute(select(Users).where(Users.unid == admin_unid))
	admin_user = admin_result.scalar_one_or_none()
	# create if it doesn't exist
	if admin_user is None:
		new_admin = Users(unid=admin_unid)
		db.add(new_admin)
		admin_created = True

	# default configuration values
	result = await db.execute(select(Configuration))
	config_exists = result.scalars().first()
	if not config_exists:
		db.add_all([
			Configuration(name="discord_tax_rate", value=5.5),
			Configuration(name="discord_msg_bonus", value=0.001),
		])
		configuration_created = True

	# view for balance (unspent coins)
	unspent_coins = text("""
		CREATE OR REPLACE VIEW v_unspent_coins AS
		SELECT
			T1.unid,
			COALESCE(SUM(T2.value), 0.00) AS sum_of_unspent_coins,
			T3.platform_id as discord_id,
			T4.platform_id as minecraft_id
		FROM users as T1
		LEFT JOIN coins AS T2 ON T1.unid = T2.unid AND T2.spent = FALSE
		LEFT JOIN discord_users AS T3 ON T1.unid = T3.unid
		LEFT JOIN minecraft_users AS T4 ON T1.unid = T4.unid
		GROUP BY T1.unid, T3.platform_id, T4.platform_id;
	""")

	# view for all balance (all coins)
	all_coins = text("""
		CREATE OR REPLACE VIEW v_all_coins AS
		SELECT
			T1.unid,
			COALESCE(SUM(T2.value), 0.00) AS sum_of_all_coins,
			T3.platform_id as discord_id,
			T4.platform_id as minecraft_id
		FROM users as T1
		LEFT JOIN coins AS T2 ON T1.unid = T2.unid
		LEFT JOIN discord_users AS T3 ON T1.unid = T3.unid
		LEFT JOIN minecraft_users AS T4 ON T1.unid = T4.unid
		GROUP BY T1.unid, T3.platform_id, T4.platform_id;
	""")

	try:
		await db.execute(unspent_coins)
		await db.execute(all_coins)
		await db.commit()
		if admin_created: log.info(f"created admin user with unid: {admin_unid}")
		if configuration_created: log.info("inserted default configuration rows")

	except Exception as e:
		await db.rollback()
		log.error("error creating default entries at main.py", e)

class Platform(str, Enum):
	discord = "discord"
	minecraft = "minecraft"

TypePlatform = Union[DiscordUsers, MinecraftUsers]

PlatformModel: Final[dict[Platform, Type[TypePlatform]]] = {
	Platform.discord: DiscordUsers,
	Platform.minecraft: MinecraftUsers
}