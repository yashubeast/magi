import enum, time
from sqlalchemy import Column, Integer, String, ForeignKey, CHAR, DECIMAL, CheckConstraint, Boolean, Enum
from sqlalchemy.orm import relationship

from utils.db import Base

class Reason(enum.Enum):
	EVAL = 'eval'
	EVAL_TAX = 'eval_tax'

class Users(Base):
	__tablename__ = 'users'

	unid = Column(Integer, primary_key=True, autoincrement=True)

	discord_users = relationship('DiscordUsers', back_populates='users')
	minecraft_users = relationship('MinecraftUsers', back_populates='users')
	coins = relationship('Coins', back_populates='users')
	coin_transfers_from = relationship('CoinTransfers', back_populates='users_from', foreign_keys='CoinTransfers.from_unid')
	coin_transfers_to = relationship('CoinTransfers', back_populates='users_to', foreign_keys='CoinTransfers.to_unid')

class DiscordUsers(Base):
	__tablename__ = 'discord_users'

	unid = Column(Integer, ForeignKey('users.unid'), primary_key=True)
	platform_id = Column(String(20), nullable=False, unique=True)
	message_count = Column(Integer, default=0)
	last_message = Column(Integer, nullable=True, default=lambda: int(time.time()))

	users = relationship('Users', back_populates='discord_users')

class DiscordMsgLogs(Base):
	__tablename__ = 'discord_msg_logs'

	id = Column(Integer, primary_key=True, autoincrement=True)
	discord_id = Column(String(20), nullable=False)
	message_id = Column(String(20), nullable=False)
	value = Column(DECIMAL(20, 2), nullable=False)
	timestamp = Column(Integer, nullable=False, default=lambda: int(time.time()))
	deleted = Column(Boolean, default=False)

class MinecraftUsers(Base):
	__tablename__ = 'minecraft_users'

	unid = Column(Integer, ForeignKey('users.unid'), primary_key=True)
	platform_id = Column(CHAR(36), nullable=False, unique=True)
	message_count = Column(Integer, default=0, nullable=False)
	last_message = Column(Integer, nullable=True)

	users = relationship('Users', back_populates='minecraft_users')

class Coins(Base):
	__tablename__ = 'coins'

	unid = Column(Integer, ForeignKey('users.unid'), nullable=False)
	coin_id = Column(Integer, primary_key=True, autoincrement=True)
	value = Column(DECIMAL(20, 2), nullable=False)
	timestamp = Column(Integer, nullable=False, default=lambda: int(time.time()))
	spent = Column(Boolean, default=False)

	users = relationship('Users', back_populates='coins')
	coin_transfers_new = relationship('CoinTransfers', back_populates='coins_new', foreign_keys='CoinTransfers.new_coin_id')
	coin_transfers_source = relationship('CoinTransfers', back_populates='coins_source', foreign_keys='CoinTransfers.source_coin_id')
	__table_args__ = (CheckConstraint('value >= 0', name='check_value_non_negative'),)

class CoinTransfers(Base):
	__tablename__ = 'coin_transfers'

	id = Column(Integer, primary_key=True, autoincrement=True)
	source_coin_id = Column(Integer, ForeignKey('coins.coin_id'), nullable=True)
	from_unid = Column(Integer, ForeignKey('users.unid'), nullable=True)
	to_unid = Column(Integer, ForeignKey('users.unid'), nullable=False)
	new_coin_id = Column(Integer, ForeignKey('coins.coin_id'), nullable=False)
	reason = Column(Enum(Reason), default=Reason.EVAL)
	timestamp = Column(Integer, nullable=False, default=lambda: int(time.time()))

	coins_new = relationship('Coins', back_populates='coin_transfers_new', foreign_keys=[new_coin_id])
	coins_source = relationship('Coins', back_populates='coin_transfers_source', foreign_keys=[source_coin_id])
	users_from = relationship('Users', back_populates='coin_transfers_from', foreign_keys=[from_unid])
	users_to = relationship('Users', back_populates='coin_transfers_to', foreign_keys=[to_unid])

class Configuration(Base):
	__tablename__ = 'configuration'

	name = Column(String(25), primary_key=True, unique=True)
	value = Column(DECIMAL(10, 5), nullable=False)