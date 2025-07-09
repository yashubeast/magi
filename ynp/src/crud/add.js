// create user
export async function user( discord_id, connection ) {
	const [result] = await connection.query(
		'INSERT IGNORE INTO users (discord_id) VALUES (?)',
		[discord_id]
	)
	return result.insertId
}

//create discord user
export async function discordUser( discord_id, connection ) {
	const [result] = await connection.query(
		'INSERT IGNORE INTO discord_users (discord_id) VALUES (?)',
		[discord_id]
	)
	return result.insertId
}

// create discord message log
export async function discordMessageLog( discord_id, message_id, value, timestamp, connection ) {
	await connection.query(
		`INSERT INTO discord_message_logs ( discord_id, message_id, value, timestamp ) VALUES (?, ?, ?, ?)`,
		[ discord_id, message_id, value, timestamp ]
	)
}

// create coin
export async function coin( UUID, value, connection ) {
	const [result] = await connection.query(
		'INSERT INTO coins (user_id, value) VALUES (?, ?)',
		[UUID, value]
	)
	return result.insertId
}

// generate a new coin
export async function genCoin( UUID, value, connection ) {

	const coinx = await coin( UUID, value, connection )

	const [transferResult] = await connection.query(
		'INSERT INTO coin_transfers (coin_id, from_user_id, to_user_id, source_coin_id) VALUES (?, ?, ?, ?)',
		[coinx, null, UUID, null]
	)
}
