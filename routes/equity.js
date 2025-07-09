import { Router } from 'express'
import { func, utils, schema, get, add } from 'ynp'
import { db } from '../db.js'

const router = Router()

router.get('/balance', async (req, res) => {
	const parsed = schema.Balance.safeParse(req.body)
	if (!parsed.success) {
		return res.status(400).json({ result: parsed.error.format() })
	}

	try {
		const { user_id } = parsed.data
		const auuid = await get.user(BigInt(user_id), db)
		const result = await get.balance(auuid, db)
		res.status(200).json({ result })
	} catch (err) {
		res.status(404).json({ result: err.message })
	}
})

router.post('/pay', async (req, res) => {
	const parsed = schema.TransferCoin.safeParse(req.body)
	if (!parsed.success) {
		return res.status(400).json({ result: parsed.error.format() })
	}

	try {
		const { sender_id, receiver_id, amount } = parsed.data
		const result = await func.transferCoin( sender_id, receiver_id, amount, db )
		res.status(200).json({ result })
	} catch (err) {
		res.status(err.status || 404).json({ result: err.message })
	}
})

router.post('/eval', async (req, res) => {
	const parsed = schema.Eval.safeParse(req.body)
	if (!parsed.success) {
		return res.status(400).json({ result: parsed.error.format() })
	}

	try {
		const { user_id, message_id, message_length, timestamp } = parsed.data
		const result = await func.evalDiscord( user_id, message_id, message_length, timestamp, db )
		res.status(200).json({ result })
	} catch (err) {
		res.status(404).json({ result: err.message })
	}
})

router.delete('/del', async (req, res) => {
	const parsed = schema.Del.safeParse(req.body)
	if (!parsed.success) {
		return res.status(400).json({ result: parsed.error.format() })
	}

	try {
		const { message_id } = parsed.data
		const result = await func.delDiscord( message_id, db )
		res.status(200).json({ result })
	} catch (err) {
		res.status(404).json({ result: err.message })
	}
})

export default router
