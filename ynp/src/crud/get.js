// get balance using UUID
export async function balance( UUID, connection ) {

	const [rows] = await connection.query(
		'SELECT COALESCE(SUM(value), 0) AS balance FROM coins WHERE user_id = ? AND spent = 0',
		[UUID]
	)
	return rows[0].balance
}

// get list of coins using UUID
export async function coins( UUID, connection ) {
	const [coins] = await connection.query(
		'SELECT coin_id, value FROM coins WHERE user_id = ? AND spent = 0 ORDER BY value ASC',
		[UUID]
	)
	return coins
}

// get list of coins to transfer using using UUID
export async function coinsToTransfer( coins, amount ) {
	let sum = 0
	const selected = []
	for ( const coin of coins ) {
		selected.push(coin)
		sum += parseFloat ( coin.value )
		if ( sum >= amount ) break
	}
	return { sum, selected }
}

// get user_id using discord_id
export async function user( discord_id, connection ) {
	const [rows] = await connection.query(
		'SELECT user_id FROM users WHERE discord_id = ? LIMIT 1',
		[discord_id]
	)

	if (rows.length == 0) throw new Error('user not found')
	return rows[0].user_id
}

// get discord user
export async function discordUser( discord_id, connection ) {
	const [rows] = await connection.query(
		'SELECT * FROM discord_users WHERE discord_id = ? LIMIT 1',
		[ discord_id ]
	)
	return rows
}

// get message bonus
export async function messageBonus(connection) {
	const [rows] = await connection.query(
		"SELECT value FROM configuration WHERE name = 'discord_message_bonus' LIMIT 1"
	)
	return rows
}

// get tax rate
export async function taxRate(connection) {
	const [rows] = await connection.query(
		"SELECT value FROM configuration WHERE name = 'discord_tax_rate' LIMIT 1"
	)
	return rows
}
