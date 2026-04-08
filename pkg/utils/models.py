from sqlalchemy.orm import mapped_column
from sqlalchemy.orm import relationship
from sqlalchemy.orm import Mapped
from sqlalchemy import CheckConstraint
from sqlalchemy import ForeignKey
from sqlalchemy import DECIMAL
from sqlalchemy import String
from sqlalchemy import Enum
from sqlalchemy import CHAR
from decimal import Decimal
from typing import Type
import secrets
import enum
import time

from . import database

# IMPORTANT
# naming conventions
# for any platforms the
# classname should be DiscordUsers aka xxxUsers
# tablename should be discord_users aka xxx_Users
# (convert classname to lowercased and insert _ where snake case triggers)
# platform name should be the xxx part aka discord (notice lowercase)

Base = database.Base

class TransactionReason(enum.Enum):
  pay = 'pay'
  genesis_message = 'genesis_message'
  genesis_playtime = 'genesis_playtime'

class TransactionPlatform(enum.Enum):
  discord = 'discord'
  minecraft = 'minecraft'

class TransactionLinkReason(enum.Enum):
  input = 'input'
  output = 'output'

class Users(Base):
  __tablename__: str = 'users'

  unid:              Mapped[str] =                mapped_column(CHAR(16), primary_key=True, default=lambda: secrets.token_hex(8))

  discord_users:     Mapped["DiscordUsers"] =     relationship(back_populates="users")
  minecraft_users:   Mapped["MinecraftUsers"] =   relationship(back_populates="users")
  coins:             Mapped["Coins"] =            relationship(back_populates='users')

class PlatformMixin:
  # registry to map platform names to their sql classes

  _registry: dict[str, Type["PlatformMixin"]] = {}

  unid:            Mapped[str] =       mapped_column(ForeignKey("users.unid"), primary_key=True)
  message_count:   Mapped[int] =       mapped_column(default=1)
  last_message:    Mapped[int] =       mapped_column(default=lambda: int(time.time()))

  def __init_subclass__(cls, **kwargs):
    super().__init_subclass__(**kwargs)
    # automatically registers the class using its __platform_name__
    if hasattr(cls, "__platform_name__"):
      PlatformMixin._registry[cls.__platform_name__] = cls

  @classmethod
  def get_class_by_name(cls, name: str) -> Type["PlatformMixin"]:
    return cls._registry.get(name)

  def __repr__(self):
    # fallback to the classname if __platform_name__ doesn't exist
    name = getattr(self, "__platform_name__", self.__class__.__name__)
    return name

class DiscordUsers(Base, PlatformMixin):
  __platform_name__: str = 'discord'
  __tablename__: str = 'discord_users'

  # unid:            Mapped[str] =       mapped_column(ForeignKey("users.unid"), primary_key=True)
  platform_id:     Mapped[str] =       mapped_column(String(24), unique=True)
  # message_count:   Mapped[int] =       mapped_column(default=1)
  # last_message:    Mapped[int] =       mapped_column(default=lambda: int(time.time()))

  users:           Mapped["Users"] =   relationship(back_populates="discord_users")

  def __repr__(self):
    return self.__platform_name__

class MinecraftUsers(Base, PlatformMixin):
  __platform_name__: str = 'minecraft'
  __tablename__: str= 'minecraft_users'

  # unid:            Mapped[str] =       mapped_column(ForeignKey('users.unid'), primary_key=True)
  platform_id:     Mapped[str] =       mapped_column(String(36), unique=True)
  # message_count:   Mapped[int] =       mapped_column(default=0)
  # last_message:    Mapped[int] =       mapped_column(default=lambda: int(time.time()))

  users:           Mapped["Users"] =   relationship(back_populates='minecraft_users')

  def __repr__(self):
    return self.__platform_name__

class Coins(Base):
  __tablename__: str = 'coins'

  unid:                Mapped[str] =                  mapped_column(ForeignKey('users.unid'))
  coin_id:             Mapped[int] =                  mapped_column(primary_key=True, autoincrement=True)
  value:               Mapped[Decimal] =              mapped_column(DECIMAL(20, 2))
  spent:               Mapped[bool] =                 mapped_column(default=False)

  users:               Mapped["Users"] =              relationship(back_populates="coins")
  transaction_links:   Mapped["TransactionLinks"] =   relationship(back_populates="coins")

  __table_args__: tuple[CheckConstraint] = (CheckConstraint('value >= 0', name='check_value_non_negative'),)

class Transactions(Base):
  __tablename__: str = 'transactions'

  txid:        Mapped[int] =   mapped_column(primary_key=True, autoincrement=True)
  reason:      Mapped[str] =   mapped_column(Enum(TransactionReason))
  platform:    Mapped[str] =   mapped_column(Enum(TransactionPlatform))
  timestamp:   Mapped[int] =   mapped_column(default=lambda: int(time.time()))

  transaction_links:   Mapped[list["TransactionLinks"]] =   relationship(back_populates="transactions")

class TransactionLinks(Base):
  __tablename__: str = 'transaction_links'

  id:             Mapped[int] =              mapped_column(primary_key=True, autoincrement=True)
  txid:           Mapped[int] =              mapped_column(ForeignKey('transactions.txid'))
  coin_id:        Mapped[int] =              mapped_column(ForeignKey('coins.coin_id'))
  type:           Mapped[str] =              mapped_column(Enum(TransactionLinkReason))

  transactions:   Mapped["Transactions"] =   relationship(back_populates="transaction_links")
  coins:          Mapped["Coins"] =          relationship(back_populates="transaction_links")

class Configuration(Base):
  __tablename__: str = 'configuration'

  name:    Mapped[str] =       mapped_column(String(25), primary_key=True)
  value:   Mapped[Decimal] =   mapped_column(DECIMAL(20, 5))
