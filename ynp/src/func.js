import Decimal from 'decimal.js'

import { utils, get, add } from 'ynp'

// p2p transfer
export async function transferCoin( sender_id, receiver_id, amount, connection, platform = "discord" ) {

	if ( sender_id === receiver_id ) { throw utils.httpError(400, 'Self transfer not allowed') }
	if ( amount <= 0 ) { throw utils.httpError(400, 'Amount must be greater than 0') }
	const conn = await connection.getConnection()

	try {
		await conn.beginTransaction()

		// get values
		let sender_user_id, receiver_user_id

		if (platform === "discord") {
			sender_user_id = await get.user(sender_id, conn)
			receiver_user_id = await get.user(receiver_id, conn)
		} else if (platform === "minecraft") {
			sender_user_id = await get.userMinecraft(sender_id, conn)
			receiver_user_id = await get.userMinecraft(receiver_id, conn)
		}

		// get balance
		const balance = await get.balance(sender_user_id, conn)
		if (balance < amount) {
			await conn.rollback()
			// return 'insufficient balance'
			throw utils.httpError(400, 'Insufficient Balance')
		}

		// get list of coins
		const coins = await get.coins(sender_user_id, conn)

		// get coins to be transferred
		const { sum, selected } = await get.coinsToTransfer(coins, amount)

		if ( sum < amount ) {
			await conn.rollback()
			// return 'insufficient balance'
			throw utils.httpError(400, 'Insufficient Balance')
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
			throw utils.httpError(404, 'Transfer Interference')
		}

		// spend the coins
		await conn.query(
			`UPDATE coins SET spent = 1 WHERE coin_id IN (${placeholders})`,
			ids
		)

		// pay the receiver
		const newCoinID = await add.coin(receiver_user_id, amount, conn)

		// return change
		let changeCoinID = null
		if (change > 0) {
			changeCoinID = await add.coin(sender_user_id, change, conn)
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
export async function evalDiscord( unique_id, string_message_id, message_length, string_timestamp, connection ) {
	const conn = await connection.getConnection()
	try {

		const message_id = BigInt(string_message_id)
		const timestamp = Number(string_timestamp)

		//fetch discord message data
		const rows = await get.discordUser( unique_id, conn )
		if (!Array.isArray(rows) || rows.length === 0) {
			await add.user(unique_id, conn)
			await add.discordUser(unique_id, conn)
		}

		// collect values for formulating
		let message_time_gap = 10
		let message_count = 1
		let last_message = null

		if (Array.isArray(rows) && rows.length > 0) {
			last_message = rows[0].last_message
			message_time_gap = (timestamp - last_message)
			message_count = rows[0].message_count
		}

		// formulate
		let time_value = message_time_gap * 0.15
		if (time_value > 1) {
			const overflow = 1.2 * Math.log( 1 + ( message_time_gap -  7  / 60 )) / Math.log(61)
			time_value = 1 + overflow
		}

		const message_bonus_row = await get.messageBonus(conn)
		const message_bonus = new Decimal(message_bonus_row[0].value).toNumber()

		let total = new Decimal(message_length)
			.mul( 1 + message_bonus * message_count )
			.mul( time_value )
			.toDecimalPlaces( 2 )
			.toNumber()
		
		// const totalValue = total
		const tax_rate_row = await get.taxRate(conn)
		const tax_rate = new Decimal(tax_rate_row[0].value).toNumber()
		// console.log('gain before tax: ', total)
		const taxAmount = total * ( tax_rate / 100 )
		const after_tax = total - taxAmount

		const totalValue = Math.floor(after_tax)
		const remainder = after_tax - totalValue
		const toAdmin = new Decimal(taxAmount + remainder).toDecimalPlaces(2).toNumber()


		// console.log('gain after tax: ', totalValue)
		// console.log('amt to admin: ', toAdmin)
		// console.log('--------------')
		if (totalValue < 1) return 0;

		// Update / create discord_users entry
		await conn.query(
			'UPDATE discord_users SET message_count = message_count + 1, last_message = ? WHERE discord_id = ?',
			[timestamp, unique_id]
		)

		// log message
		await add.discordMessageLog( unique_id, message_id, totalValue, timestamp, conn )

		await add.coin(0, toAdmin, conn)
		const auuid = await get.user(unique_id, conn)
		await add.genCoin(auuid, totalValue, conn)

		return totalValue
	} finally {
		conn.release()
	}
}

export async function delDiscord( string_message_id, connection ) {
	const conn = await connection.getConnection()
	try {
		await conn.beginTransaction()
		// const user_id = BigInt(string_user_id)
		const message_id = BigInt(string_message_id)
		const [r] = await conn.query(
			'UPDATE discord_message_logs SET deleted = 1 WHERE message_id = ?',
			[ message_id ]
		)

		if (!r.affectedRows) {
			throw utils.httpError(400, 'out of scope')
		}

		const [[ amount_row ]] = await conn.query(
			'SELECT value, discord_id FROM discord_message_logs WHERE message_id = ? LIMIT 1',
			[ message_id ]
		)
		const discord_id = BigInt(amount_row.discord_id)

		const [[ uuid_row ]] = await conn.query(
			'SELECT user_id FROM users WHERE discord_id = ? LIMIT 1',
			[ discord_id ]
		)
		const user_id = parseInt(uuid_row.user_id)

		await conn.query(
			'UPDATE discord_users SET message_count = message_count - 1 WHERE discord_id = ?',
			[ discord_id ]
		)
		const amount = new Decimal( amount_row.value )
		const auuid = await get.user(discord_id, conn)
		const coins = await get.coins(auuid, conn)
		const { sum, selected } = await get.coinsToTransfer(coins, amount)
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
			throw utils.httpError(404, 'Transfer Inteference')
		}

		// spend the coins
		await conn.query(
			`UPDATE coins SET spent = 1 WHERE coin_id IN (${placeholders})`,
			ids
		)

		// pay admin
		const newCoinID = await add.coin(0, sum, conn)

		// return change
		let changeCoinID = null
		if (change > 0) {
			changeCoinID = await add.coin(user_id, change, conn)
		}

		// receiver coin transfer
		const receiverTransfers = selected.map( c =>
			conn.query(
				'INSERT INTO coin_transfers (coin_id, from_user_id, to_user_id, source_coin_id) VALUES (?, ?, ?, ?)',
				[newCoinID, auuid, 0, c.coin_id]
			)
		)

		// sender coin transfer
		const senderTransfers = changeCoinID
			? selected.map( c =>
				conn.query(
					'INSERT INTO coin_transfers (coin_id, from_user_id, to_user_id, source_coin_id) VALUES (?, ?, ?, ?)',
					[changeCoinID, user_id, user_id, c.coin_id]
				))
			: []

		// create coin_transfers for each source coin
		await Promise.all([...receiverTransfers, ...senderTransfers])

		await conn.commit()
		return amount
	} catch (err) {
			await conn.rollback()
			throw err
	} finally {
		conn.release()
	}
}

// eval minecraft
export async function evalMinecraft( minecraft_id, message_length, string_timestamp, connection ) {
	const conn = await connection.getConnection()
	try {

		const unique_id = minecraft_id
		const timestamp = Number(string_timestamp)

		//fetch discord message data
		const rows = await get.minecraftUser( unique_id, conn )
		if (!Array.isArray(rows) || rows.length === 0) {
			const temp_id = await add.realuser(conn)
			await add.minecraftUser(temp_id, unique_id, conn)
		}

		// collect values for formulating
		let message_time_gap = 10
		let message_count = 1
		let last_message = null

		if (Array.isArray(rows) && rows.length > 0) {
			last_message = rows[0].last_message
			message_time_gap = (timestamp - last_message)
			message_count = rows[0].message_count
		}

		// formulate
		let time_value = message_time_gap * 0.15
		if (time_value > 1) {
			const overflow = 1.2 * Math.log( 1 + ( message_time_gap -  7  / 60 )) / Math.log(61)
			time_value = 1 + overflow
		}

		const message_bonus_row = await get.messageBonus(conn)
		const message_bonus = new Decimal(message_bonus_row[0].value).toNumber()

		let total = new Decimal(message_length)
			.mul( 1 + message_bonus * message_count )
			.mul( time_value )
			.toDecimalPlaces( 2 )
			.toNumber()
		
		// const totalValue = total
		const tax_rate_row = await get.taxRate(conn)
		const tax_rate = new Decimal(tax_rate_row[0].value).toNumber()
		// console.log('gain before tax: ', total)
		const taxAmount = total * ( tax_rate / 100 )
		const after_tax = total - taxAmount

		const totalValue = Math.floor(after_tax)
		const remainder = after_tax - totalValue
		const toAdmin = new Decimal(taxAmount + remainder).toDecimalPlaces(2).toNumber()


		// console.log('gain after tax: ', totalValue)
		// console.log('amt to admin: ', toAdmin)
		// console.log('--------------')
		if (totalValue < 1) return 0;

		// Update / create discord_users entry
		await conn.query(
			'UPDATE minecraft_users SET message_count = message_count + 1, last_message = ? WHERE minecraft_id = ?',
			[timestamp, unique_id]
		)

		await add.coin(0, toAdmin, conn)
		const auuid = await get.userMinecraft(unique_id, conn)
		await add.genCoin(auuid, totalValue, conn)

		return totalValue
	} finally {
		conn.release()
	}
}
