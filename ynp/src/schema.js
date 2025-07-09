import { z } from 'zod'

export const Eval = z.object({
	user_id: z.string(),
	message_id: z.string(),
	message_length: z.number().int(),
	timestamp: z.string()
})

export const Del = z.object({
	message_id: z.string()
})

export const TransferCoin = z.object({
	sender_id: z.string(),
	receiver_id: z.string(),
	amount: z.number().int()
})

export const Balance = z.object({
	user_id: z.string()
})
