import { Router }from 'express'

import { SchemaTransferCoin, SchemaBalance } from '../utils/schemas.js'
import { getBalanceByUniqueID, transferCoin } from '../utils/crud.js'

const router = Router()

router.get('/balance', async (req, res) => {
	const parsed = SchemaBalance.safeParse(req.body)
	if (!parsed.success) {
		return res.status(400).json({ result: parsed.error.format() })
	}

	try {
		const { unique_id } = parsed.data
		const result = await getBalanceByUniqueID(unique_id)
		res.status(200).json({ result })
	} catch (err) {
		res.status(404).json({ result: err.message })
	}
})

router.post('/pay', async (req, res) => {
	const parsed = SchemaTransferCoin.safeParse(req.body)
	if (!parsed.success) {
		return res.status(400).json({ result: parsed.error.format() })
	}

	try {
		const { sender_id, receiver_id, amount } = parsed.data
		const result = await transferCoin( sender_id, receiver_id, amount )
		res.status(200).json({ result })
	} catch (err) {
		res.status(404).json({ result: err.message })
	}
})

export default router
