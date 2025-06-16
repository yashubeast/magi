import db from './database/db.js'

// get user_id using unique_id
export async function getUser(unique_id, connection = db) {
	const [rows] = await connection.query(
		'SELECT user_id FROM users WHERE discord_id = ? LIMIT 1',
		[unique_id]
	)

	if (rows.length == 0) throw new Error('user not found')
	return rows[0].user_id
}

// get balance using user_id
export async function getBalanceByUserID(user_id, connection = db) {

	const [rows] = await connection.query(
		'SELECT COALESCE(SUM(value), 0) AS balance FROM coins WHERE user_id = ? AND spent = 0',
		[user_id]
	)

	return rows[0].balance
}

// get balance using unique_id
export async function getBalanceByUniqueID(unique_id, connection = db) {
	const user_id = await getUser(unique_id, connection)
	const balance = await getBalanceByUserID(user_id, connection)

	return balance
}

// get list of coins using user_id
async function getCoins(user_id, connection = db) {
	const [coins] = await connection.query(
		'SELECT coin_id, value FROM coins WHERE user_id = ? AND spent = 0 ORDER BY value ASC',
		[user_id]
	)
	return coins
}

// get list of coins to transfer using using user_id
async function getCoinsToTransfer(coins, amount) {
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
async function createCoin(user_id, value, connection = db) {
	const [result] = await connection.query(
		'INSERT INTO coins (user_id, value) VALUES (?, ?)',
		[user_id, value]
	)
	return result.insertId
}


export async function transferCoin(sender_id, receiver_id, amount) {
	if ( sender_id == receiver_id ) { return 'self transfer not allowed' }
	const conn = await db.getConnection()

	try {
		await conn.beginTransaction()

		// get values
		const sender_user_id = await getUser(sender_id, conn)
		const receiver_user_id = await getUser(receiver_id, conn)

		// get balance
		const balance = await getBalanceByUserID(sender_user_id, conn)
		if (balance < amount) {
			await conn.rollback()
			return 'insufficient balance'
		}

		// get list of coins
		const coins = await getCoins(sender_user_id, conn)

		// get coins to be transferred
		const { sum, selected } = await getCoinsToTransfer(coins, amount)

		if ( sum < amount ) {
			await conn.rollback()
			return 'insufficient balance'
		}
		const change = sum - amount

		const ids = selected.map( c => c.coin_id )
		const placeholders = ids.map(() => '?').join(', ')

		// lock the coins to be spent
		const [locked] = await conn.query(
			`SELECT spent FROM coins WHERE coin_id IN (${placeholders}) FOR UPDATE`,
			ids
		)
		if (locked.some( c => c.spent)) {
			await conn.rollback()
			return 'spent coins interference'
		}

		// spend the coins
		await conn.query(
			`UPDATE coins SET spent = 1 WHERE coin_id IN (${placeholders})`,
			ids
		)

		// pay the receiver
		const newCoinID = await createCoin(receiver_user_id, amount, conn)

		// return change
		let changeCoinID = null
		if (change > 0) {
			changeCoinID = await createCoin(sender_user_id, change, conn)
		}

		// receiver coin transfer
		const receiverTransfers = selected.map( c =>
			conn.query(
				'INSERT INTO coin_transfers (coin_id, from_user_id, to_user_id, source_coin_id) VALUES (?, ?, ?, ?)',
				[newCoinID, sender_user_id, receiver_user_id, c.coin_id]
			)
		)

		// sender coin transfer
		const senderTransfers = changeCoinID
			? selected.map( c =>
				conn.query(
					'INSERT INTO coin_transfers (coin_id, from_user_id, to_user_id, source_coin_id) VALUES (?, ?, ?, ?)',
					[changeCoinID, sender_user_id, sender_user_id, c.coin_id]
				))
			: []

		// create coin_transfers for each source coin
		await Promise.all([...receiverTransfers, ...senderTransfers])

		await conn.commit()
		return true
	} catch (err) {
			await conn.rollback()
			throw err
	} finally {
			conn.release()
	}
}
