import { Router }from 'express'
import * as ynp from 'ynp'
import { db } from '../db.js'

const router = Router()

router.get('/balance', async (req, res) => {
	const parsed = ynp.SchemaBalance.safeParse(req.body)
	if (!parsed.success) {
		return res.status(400).json({ result: parsed.error.format() })
	}

	try {
		const { user_id } = parsed.data
		const auuid = await ynp.getUser(BigInt(user_id), db)
		const result = await ynp.getBalance(auuid, db)
		res.status(200).json({ result })
	} catch (err) {
		res.status(404).json({ result: err.message })
	}
})

router.post('/pay', async (req, res) => {
	const parsed = ynp.SchemaTransferCoin.safeParse(req.body)
	if (!parsed.success) {
		return res.status(400).json({ result: parsed.error.format() })
	}

	try {
		const { sender_id, receiver_id, amount } = parsed.data
		const result = await ynp.transferCoin( sender_id, receiver_id, amount, db )
		res.status(200).json({ result })
	} catch (err) {
		res.status(404).json({ result: err.message })
	}
})

router.post('/eval', async (req, res) => {
	const parsed = ynp.SchemaEval.safeParse(req.body)
	if (!parsed.success) {
		return res.status(400).json({ result: parsed.error.format() })
	}

	try {
		const { user_id, message_id, message_length, timestamp } = parsed.data
		const result = await ynp.evalDiscord( user_id, message_id, message_length, timestamp, db )
		res.status(200).json({ result })
	} catch (err) {
		res.status(404).json({ result: err.message })
	}
})

router.delete('/del', async (req, res) => {
	const parsed = ynp.SchemaDel.safeParse(req.body)
	if (!parsed.success) {
		return res.status(400).json({ result: parsed.error.format() })
	}

	try {
		const { user_id, message_id } = parsed.data
		const result = await ynp.del( user_id, message_id, db )
		res.status(200).json({ result })
	} catch (err) {
		res.status(404).json({ result: err.message })
	}
})

export default router
