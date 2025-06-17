// create user
export async function createUser( discord_id, connection ) {
	const [result] = await connection.query(
		'INSERT INTO users (discord_id) VALUES (?)',
		[discord_id]
	)
	return result.insertId
}

//create discord user
export async function createDiscordUser( discord_id, connection ) {
	const [result] = await connection.query(
		'INSERT INTO discord_users (discord_id) VALUES (?)',
		[discord_id]
	)
	return result.insertId
}

// create discord message log
export async function createDiscordMessageLog( discord_id, message_id, value, timestamp, connection ) {
	await connection.query(
		`INSERT INTO discord_message_logs ( discord_id, message_id, value, timestamp ) VALUES (?, ?, ?, ?)`,
		[ discord_id, message_id, value, timestamp ]
	)
}

// get user_id using discord_id
export async function getUser( discord_id, connection ) {
	const [rows] = await connection.query(
		'SELECT user_id FROM users WHERE discord_id = ? LIMIT 1',
		[discord_id]
	)

	if (rows.length == 0) throw new Error('user not found')
	return rows[0].user_id
}

// get discord user
export async function getDiscordUser( discord_id, connection ) {
	const [rows] = await connection.query(
		'SELECT * FROM discord_users WHERE discord_id = ? LIMIT 1',
		[ discord_id ]
	)
	return rows
}

// get message bonus
export async function getMessageBonus(connection) {
	const [rows] = await connection.query(
		"SELECT value FROM configuration WHERE name = 'discord_message_bonus' LIMIT 1"
	)
	return rows
}

// get tax rate
export async function getTaxRate(connection) {
	const [rows] = await connection.query(
		"SELECT value FROM configuration WHERE name = 'discord_tax_rate' LIMIT 1"
	)
	return rows
}
