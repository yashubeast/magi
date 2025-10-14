import enum
import time
import secrets
from sqlalchemy import String
from sqlalchemy import Table
from sqlalchemy import MetaData
from sqlalchemy import ForeignKey
from sqlalchemy import DECIMAL
from sqlalchemy import CheckConstraint
from sqlalchemy import Enum
from sqlalchemy import CHAR
from sqlalchemy import Column
from sqlalchemy.orm import relationship
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from typing import Optional
from decimal import Decimal

from . import database

Base = database.Base
ViewBase = declarative_base()

class CoinTransferReason(enum.Enum):
	Eval = 'eval'
	EvalTax = 'eval_tax'

class Users(Base):
	__tablename__ = 'users'

	unid: Mapped[str] = mapped_column(CHAR(16), primary_key=True, default=lambda: secrets.token_hex(8))

	discord_users:     Mapped["DiscordUsers"] =     relationship(back_populates="users")
	minecraft_users:   Mapped["MinecraftUsers"] =   relationship(back_populates="users")
	coins:             Mapped["Coins"] =            relationship(back_populates='users')
	coin_transfers_from_user: Mapped[list["CoinTransfers"]] = relationship(
		foreign_keys="CoinTransfers.from_unid", back_populates="from_user"
	)
	coin_transfers_to_user: Mapped[list["CoinTransfers"]] = relationship(
		foreign_keys="CoinTransfers.to_unid", back_populates="to_user"
	)

class DiscordUsers(Base):
	__tablename__ = 'discord_users'

	unid:            Mapped[str] =   mapped_column(ForeignKey("users.unid"), primary_key=True)
	platform_id:     Mapped[str] =   mapped_column(String(24), unique=True)
	message_count:   Mapped[int] =   mapped_column(default=0)
	last_message:    Mapped[int] =   mapped_column(default=lambda: int(time.time()))

	users: Mapped["Users"] = relationship(back_populates="discord_users")

class DiscordMsgLogs(Base):
	__tablename__ = 'discord_msg_logs'

	id:           Mapped[int] =       mapped_column(primary_key=True, autoincrement=True)
	discord_id:   Mapped[str] =       mapped_column(String(24))
	message_id:   Mapped[str] =       mapped_column(String(24))
	value:        Mapped[Decimal] =   mapped_column(DECIMAL(20, 2))
	timestamp:    Mapped[int] =       mapped_column(default=lambda: int(time.time()))
	deleted:      Mapped[bool] =      mapped_column(default=False)

class MinecraftUsers(Base):
	__tablename__ = 'minecraft_users'

	unid:            Mapped[str] =   mapped_column(ForeignKey('users.unid'), primary_key=True)
	platform_id:     Mapped[str] =   mapped_column(String(36), unique=True)
	message_count:   Mapped[int] =   mapped_column(default=0)
	last_message:    Mapped[int] =   mapped_column(default=lambda: int(time.time()))

	users: Mapped["Users"] = relationship(back_populates='minecraft_users')

class Coins(Base):
	__tablename__ = 'coins'

	unid:        Mapped[str] =       mapped_column(ForeignKey('users.unid'))
	coin_id:     Mapped[int] =       mapped_column(primary_key=True, autoincrement=True)
	value:       Mapped[Decimal] =   mapped_column(DECIMAL(20, 2))
	timestamp:   Mapped[int] =       mapped_column(default=lambda: int(time.time()))
	spent:       Mapped[bool] =      mapped_column(default=False)

	users:            Mapped["Users"] =           relationship(back_populates='coins')
	coin_transfers_source_coin: Mapped[list["CoinTransfers"]] = relationship(
		foreign_keys="CoinTransfers.source_coin_id", back_populates='source_coin'
	)
	coin_transfers_new_coin: Mapped[list["CoinTransfers"]] = relationship(
		foreign_keys="CoinTransfers.new_coin_id", back_populates="new_coin"
	)

	__table_args__ = (CheckConstraint('value >= 0', name='check_value_non_negative'),)

class CoinTransfers(Base):
	__tablename__ = 'coin_transfers'

	id:               Mapped[int] =             mapped_column(primary_key=True, autoincrement=True)
	source_coin_id:   Mapped[Optional[int]] =   mapped_column(ForeignKey('coins.coin_id'))
	from_unid:        Mapped[Optional[str]] =   mapped_column(ForeignKey('users.unid'))
	to_unid:          Mapped[str] =             mapped_column(ForeignKey('users.unid'))
	new_coin_id:      Mapped[int] =             mapped_column(ForeignKey('coins.coin_id'))
	reason:           Mapped[str] =             mapped_column(Enum(CoinTransferReason), default=CoinTransferReason.Eval)
	timestamp:        Mapped[int] =             mapped_column(default=lambda: int(time.time()))

	source_coin:   Mapped["Coins"] =   relationship(foreign_keys=[source_coin_id], back_populates='coin_transfers_source_coin')
	new_coin:   Mapped["Coins"] =      relationship(foreign_keys=[new_coin_id], back_populates='coin_transfers_new_coin')
	from_user:   Mapped["Users"] =     relationship(foreign_keys=[from_unid], back_populates='coin_transfers_from_user')
	to_user:   Mapped["Users"] =       relationship(foreign_keys=[to_unid], back_populates='coin_transfers_to_user')

class Configuration(Base):
	__tablename__ = 'configuration'

	name:    Mapped[str] =       mapped_column(String(25), primary_key=True)
	value:   Mapped[Decimal] =   mapped_column(DECIMAL(20, 5))

### views ###

class VUnspentCoins(ViewBase):
	__table__ = Table(
		'v_unspent_coins',
		MetaData(),
		Column('unid', String, ForeignKey("users.unid"), primary_key=True),
		Column('sum_of_unspent_coins', DECIMAL(20,2)),
		Column('discord_id', String(24)),
		Column('minecraft_id', String(36))
	)
	unid: Mapped[str]
	sum_of_unspent_coins: Mapped[Decimal]
	discord_id: Mapped[Optional[str]]
	minecraft_id: Mapped[Optional[str]]

class VAllCoins(ViewBase):
	__table__ = Table(
		'v_all_coins',
		MetaData(),
		Column('unid', String, ForeignKey("users.unid"), primary_key=True),
		Column('sum_of_all_coins', DECIMAL(20,2)),
		Column('discord_id', String(24)),
		Column('minecraft_id', String(36))
	)
	unid: Mapped[str]
	sum_of_all_coins: Mapped[Decimal]
	discord_id: Mapped[Optional[str]]
	minecraft_id: Mapped[Optional[str]]