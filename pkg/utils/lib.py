from sqlalchemy.ext.asyncio import AsyncSession
from collections import defaultdict
from sqlalchemy import select
from sqlalchemy import text
from typing import TypeVar
import asyncio

from .models import TransactionPlatform
from .models import MinecraftUsers
from .models import Configuration
from .models import DiscordUsers
from .models import Users
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
      Configuration(name="discord_tax_rate", value=96.4),
      Configuration(name="discord_msg_bonus", value=0.001),
    ])
    configuration_created = True

  # view for a lot of things
  view_all = text("""
    CREATE OR REPLACE VIEW v_all AS
    SELECT
      T1.unid,
      COALESCE(SUM(T2.value), 0.00) AS sigma_coins,
      COALESCE(SUM(CASE WHEN T2.spent = FALSE THEN T2.value ELSE 0.00 END), 0.00) AS balance,
      T3.platform_id as dc_id,
      T4.platform_id as mc_id,
      T3.message_count as dc_messages,
      T4.message_count as mc_messages
    FROM users as T1
    LEFT JOIN coins AS T2 ON T1.unid = T2.unid
    LEFT JOIN discord_users AS T3 ON T1.unid = T3.unid
    LEFT JOIN minecraft_users AS T4 ON T1.unid = T4.unid
    GROUP BY T1.unid, T3.platform_id, T4.platform_id;
  """)

  try:
    _ = await db.execute(view_all)
    await db.commit()
    if admin_created:
      log.info(f"created admin user with unid: {admin_unid}")
    if configuration_created:
      log.info("inserted default configuration rows")

  except Exception as e:
    await db.rollback()
    log.error("error creating default entries at main.py", e)









class PlatformToEnumLink:

  _links = {}
  _links_reversed = {}

  @classmethod
  def initialize(cls):
    # build mappings to avoid circular imports
    cls._links = {
      DiscordUsers: TransactionPlatform.discord,
      MinecraftUsers: TransactionPlatform.minecraft
    }
    cls._links_reversed = {v: k for k, v in cls._links.items()}

  @classmethod
  def get_enum_using_class(cls, platform_class: type) -> TransactionPlatform:
    if not cls._links: cls.initialize()

    try:
      return cls._links[platform_class]
    except KeyError:
      log.error("error finding enum using class")
      raise ValueError

  @classmethod
  def get_class_using_enum(cls, enum: TransactionPlatform) -> type:
    if not cls._links_reversed: cls.initialize()

    try:
      return cls._links_reversed[enum]
    except KeyError:
      log.error("error finding class using enum")
      raise ValueError

TypePlatform = TypeVar("TypePlatform", bound= DiscordUsers | MinecraftUsers)

class UserEval:

  def __init__(
    self,
    current_time: int,
    message_length: int
  ):
    self.current_time = current_time
    self.message_length = message_length

  def __repr__(self):
    return f"time: {self.current_time}, len: {self.message_length}"

PayoutQueueLock = asyncio.Lock()
PayoutQueue: dict[type[DiscordUsers|MinecraftUsers], dict[str, dict[str, list[UserEval]]]] = defaultdict(
  lambda: defaultdict(
    lambda: defaultdict(list)
  )
)

class PlatformAcitivities:
  message = 'message'
