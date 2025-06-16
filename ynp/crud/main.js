// get balance using UUID
export async function getBalance( UUID, connection ) {

	const [rows] = await connection.query(
		'SELECT COALESCE(SUM(value), 0) AS balance FROM coins WHERE user_id = ? AND spent = 0',
		[UUID]
	)

	return rows[0].balance
}
//
// get list of coins using UUID
async function getCoins( UUID, connection ) {
	const [coins] = await connection.query(
		'SELECT coin_id, value FROM coins WHERE user_id = ? AND spent = 0 ORDER BY value ASC',
		[UUID]
	)
	return coins
}

// get list of coins to transfer using using UUID
async function getCoinsToTransfer( coins, amount ) {
	let sum = 0
	const selected = []
	for ( const coin of coins ) {
		selected.push(coin)
		sum += parseFloat ( coin.value )
		if ( sum >= amount ) break
	}
	return { sum, selected }
}

// create coin
async function createCoin( UUID, value, connection ) {
	const [result] = await connection.query(
		'INSERT INTO coins (user_id, value) VALUES (?, ?)',
		[UUID, value]
	)
	return result.insertId
}
