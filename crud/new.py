from decimal import Decimal
from typing import Optional, Type, TypeVar
from utils.models import Users, DiscordUsers, MinecraftUsers, Coins, CoinTransfers, Reason
from sqlalchemy.orm import Session

def user(db: Session) -> Optional[int]:
	try:
		new_user = Users()
		db.add(new_user)
		db.commit()
		db.refresh(new_user)
		return new_user.unid
	except Exception:
		db.rollback()
		return None

T = TypeVar("T", DiscordUsers, MinecraftUsers)
def platform_user(model: Type[T], platform_id: str, db: Session) -> Optional[int]:
	try:
		unid = user(db)
		new_user = model(
			unid=unid,
			platform_id=platform_id
		)
		db.add(new_user)
		db.commit()
		return unid
	except Exception:
		db.rollback()
		return None

def eval_coin(unid: int, value: Decimal, to_admin: Decimal, db: Session):
	new_coin = Coins(unid = unid, value = value)
	db.add(new_coin)
	db.commit()
	db.refresh(new_coin)
	new_coin_trans = CoinTransfers(to_unid = unid, new_coin_id = new_coin.coin_id)
	db.add(new_coin_trans)
	db.commit()
	# to admin
	admin_coin = Coins(unid = 0, value = to_admin)
	db.add(admin_coin)
	db.commit()
	db.refresh(admin_coin)
	admin_coin_trans = CoinTransfers(source_coin_id = new_coin.coin_id, from_unid = unid, to_unid = 0, new_coin_id = admin_coin.coin_id, reason = Reason.EVAL_TAX)
	db.add(admin_coin_trans)
	db.commit()
	return