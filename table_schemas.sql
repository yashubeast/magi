CREATE TABLE IF NOT EXISTS users (
	user_id INT PRIMARY KEY AUTO_INCREMENT,
	discord_id BIGINT UNIQUE
);

SET sql_mode = 'NO_AUTO_VALUE_ON_ZERO';
INSERT IGNORE INTO users (user_id) VALUES (0);

CREATE TABLE IF NOT EXISTS coins (
	coin_id INT PRIMARY KEY AUTO_INCREMENT,
	user_id INT NOT NULL,
	value NUMERIC(20, 2) NOT NULL CHECK (value > 0),
	created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	spent TINYINT(1) DEFAULT 0,
	FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS coin_transfers (
	id INT PRIMARY KEY AUTO_INCREMENT,
	coin_id INT NOT NULL,
	from_user_id INT,
	to_user_id INT NOT NULL,
	transferred_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	source_coin_id INT,
	FOREIGN KEY (coin_id) REFERENCES coins(coin_id) ON DELETE CASCADE,
	FOREIGN KEY (to_user_id) REFERENCES users(user_id),
	FOREIGN KEY (source_coin_id) REFERENCES coins(coin_id)
);

CREATE TABLE IF NOT EXISTS configuration (
	name VARCHAR(25) PRIMARY KEY UNIQUE,
	value DECIMAL(10, 5)
);

INSERT IGNORE INTO configuration (name, value) VALUES ('discord_tax_rate', 5.5);
INSERT IGNORE INTO configuration (name, value) VALUES ('discord_message_bonus', 0.001);

CREATE TABLE IF NOT EXISTS discord_message_logs (
	id INT PRIMARY KEY AUTO_INCREMENT,
	discord_id BIGINT NOT NULL,
	message_id BIGINT NOT NULL,
	value NUMERIC(20, 2) NOT NULL CHECK (value > 0),
	timestamp DOUBLE NOT NULL,
	deleted TINYINT(1) DEFAULT 0
);

CREATE TABLE IF NOT EXISTS discord_users (
	id INT PRIMARY KEY AUTO_INCREMENT,
	discord_id BIGINT NOT NULL UNIQUE,
	message_count INT DEFAULT 0,
	last_message DOUBLE NULL,
	FOREIGN KEY (discord_id) REFERENCES users(discord_id) ON DELETE CASCADE
);
