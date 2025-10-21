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
import secrets
import enum
import time

from . import database

Base = database.Base

class TransactionReason(enum.Enum):
	genesis = 'genesis'
	pay = 'pay'

class TransactionLinkReason(enum.Enum):
	input = 'input'
	output = 'output'

class Users(Base):
	__tablename__: str = 'users'

	unid: Mapped[str] = mapped_column(CHAR(16), primary_key=True, default=lambda: secrets.token_hex(8))

	discord_users:     Mapped["DiscordUsers"] =     relationship(back_populates="users")
	minecraft_users:   Mapped["MinecraftUsers"] =   relationship(back_populates="users")
	coins:             Mapped["Coins"] =            relationship(back_populates='users')
	# coin_transfers_from_user: Mapped[list["Transactions"]] = relationship(
	# 	foreign_keys="CoinTransfers.from_unid", back_populates="from_user"
	# )
	# coin_transfers_to_user: Mapped[list["Transactions"]] = relationship(
	# 	foreign_keys="CoinTransfers.to_unid", back_populates="to_user"
	# )

class DiscordUsers(Base):
	__tablename__: str = 'discord_users'

	unid:            Mapped[str] =   mapped_column(ForeignKey("users.unid"), primary_key=True)
	platform_id:     Mapped[str] =   mapped_column(String(24), unique=True)
	message_count:   Mapped[int] =   mapped_column(default=0)
	last_message:    Mapped[int] =   mapped_column(default=lambda: int(time.time()))

	users: Mapped["Users"] = relationship(back_populates="discord_users")

class MinecraftUsers(Base):
	__tablename__: str= 'minecraft_users'

	unid:            Mapped[str] =   mapped_column(ForeignKey('users.unid'), primary_key=True)
	platform_id:     Mapped[str] =   mapped_column(String(36), unique=True)
	message_count:   Mapped[int] =   mapped_column(default=0)
	last_message:    Mapped[int] =   mapped_column(default=lambda: int(time.time()))

	users: Mapped["Users"] = relationship(back_populates='minecraft_users')

class Coins(Base):
	__tablename__: str = 'coins'

	unid:        Mapped[str] =       mapped_column(ForeignKey('users.unid'))
	coin_id:     Mapped[int] =       mapped_column(primary_key=True, autoincrement=True)
	value:       Mapped[Decimal] =   mapped_column(DECIMAL(20, 2))
	# timestamp:   Mapped[int] =       mapped_column(default=lambda: int(time.time()))
	spent:       Mapped[bool] =      mapped_column(default=False)

	users:                 Mapped["Users"] =              relationship(back_populates="coins")
	transaction_links:     Mapped["TransactionLinks"] =   relationship(back_populates="coins")

	__table_args__: tuple[CheckConstraint] = (CheckConstraint('value >= 0', name='check_value_non_negative'),)

class Transactions(Base):
	__tablename__: str = 'transactions'

	txid:               Mapped[int] =             mapped_column(primary_key=True, autoincrement=True)
	# from_unid:        Mapped[Optional[str]] =   mapped_column(ForeignKey('users.unid'))
	# to_unid:          Mapped[str] =             mapped_column(ForeignKey('users.unid'))
	reason:           Mapped[str] =             mapped_column(Enum(TransactionReason))
	timestamp:        Mapped[int] =             mapped_column(default=lambda: int(time.time()))

	transaction_links:   Mapped["TransactionLinks"] =   relationship(back_populates="transactions")
	# from_user:   Mapped["Users"] =     relationship(foreign_keys=[from_unid], back_populates='coin_transfers_from_user')
	# to_user:   Mapped["Users"] =       relationship(foreign_keys=[to_unid], back_populates='coin_transfers_to_user')

class TransactionLinks(Base):
	__tablename__: str = 'transaction_links'

	id: Mapped[int] =        mapped_column(primary_key=True, autoincrement=True)
	txid: Mapped[int] =      mapped_column(ForeignKey('transactions.txid'))
	coin_id: Mapped[int] =   mapped_column(ForeignKey('coins.coin_id'))
	type: Mapped[str] =      mapped_column(Enum(TransactionLinkReason))

	transactions:   Mapped["Transactions"] =   relationship(back_populates="transaction_links")
	coins:          Mapped["Coins"] =          relationship(back_populates="transaction_links")

class Configuration(Base):
	__tablename__: str = 'configuration'

	name:    Mapped[str] =       mapped_column(String(25), primary_key=True)
	value:   Mapped[Decimal] =   mapped_column(DECIMAL(20, 5))