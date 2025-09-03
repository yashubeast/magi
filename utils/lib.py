from sqlalchemy import text
from sqlalchemy.orm import Session
from utils.models import Configuration

def default_rows(db: Session):
	# wacky way to set sudo account in users table
	db.execute(text("SET SESSION sql_mode = CONCAT_WS(',', @@sql_mode, 'NO_AUTO_VALUE_ON_ZERO')"))
	db.execute(text("INSERT IGNORE INTO users (unid) VALUES (0)"))

	# default configuration values
	if not db.query(Configuration).first():
		db.add_all([
			Configuration(name="discord_tax_rate", value=5.5),
			Configuration(name="discord_msg_bonus", value=0.001),
		])
	db.commit()