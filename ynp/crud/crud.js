import * as main from './main.js'
import * as discord from './discord.js'
import Decimal from 'decimal.js'

// p2p transfer
export async function transferCoin( sender_id, receiver_id, amount, connection ) {
	if ( sender_id == receiver_id ) { return 'self transfer not allowed' }
	const conn = await connection.getConnection()

	try {
		await conn.beginTransaction()

		// get values
		const sender_user_id = await discord.getUser(sender_id, conn)
		const receiver_user_id = await discord.getUser(receiver_id, conn)

		// get balance
		const balance = await main.getBalance(sender_user_id, conn)
		if (balance < amount) {
			await conn.rollback()
			return 'insufficient balance'
		}

		// get list of coins
		const coins = await main.getCoins(sender_user_id, conn)

		// get coins to be transferred
		const { sum, selected } = await main.getCoinsToTransfer(coins, amount)

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
		const newCoinID = await main.createCoin(receiver_user_id, amount, conn)

		// return change
		let changeCoinID = null
		if (change > 0) {
			changeCoinID = await main.createCoin(sender_user_id, change, conn)
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


// eval
export async function evalDiscord( unique_id, message_id, message_length, timestamp, connection ) {
	const conn = await connection.getConnection()
	try {

		//fetch discord message data
		const rows = await discord.getDiscordUser( unique_id, conn )
		if (!Array.isArray(rows) || rows.length === 0) {
			await discord.createUser(unique_id, conn)
			await discord.createDiscordUser(unique_id, conn)
		}

		// collect values for formulating
		let message_time_gap = 2
		let message_count = 1
		let last_message = null

		if (Array.isArray(rows) && rows.length > 0) {
			last_message = new Date(rows[0].last_message)
			message_time_gap = (new Date(timestamp) - last_message) / 1000
			message_count = rows[0].message_count
		}

		// formulate
		let time_value = message_time_gap * 0.15
		if (time_value > 1) {
			const overflow = 1.2 * Math.log( 1 + ( message_time_gap - ( 7  / 60 ))) / Math.log(61)
			// const overflow = 1.2 * Math.log( 1 + (( message_time_gap - 7 ) / 60 )) / Math.log(61)
			time_value = 1 + overflow
		}
		let total = new Decimal(message_length)
			.mul( 1 + 0.001 * message_count )
			.mul( time_value )
			.toDecimalPlaces( 2 )
		
		const totalValue = total.toNumber()

		console.log(totalValue)
		if (totalValue < 1) return 0;

		// Update / create discord_users entry
		await conn.query(`
			INSERT INTO discord_users ( discord_id, message_count, last_message )
			VALUES ( ?, 1, ? )
			ON DUPLICATE KEY UPDATE
				message_count = message_count + 1,
				last_message = ?
		`, [unique_id, timestamp, timestamp])

		// log message
		await discord.createDiscordMessageLog( unique_id, message_id, totalValue, timestamp, conn )

		const auuid = await discord.getUser(unique_id, conn)
		await main.genCoin(auuid, totalValue, conn)

		return true
	} finally {
		conn.release()
	}
}
