import { z } from 'zod'

export const SchemaEval = z.object({
	unique_id: z.number().int(),
	message_id: z.number().int(),
	message_length: z.number().int(),
	timestamp: z.number()
})

export const SchemaTransferCoin = z.object({
	sender_id: z.number().int(),
	receiver_id: z.number().int(),
	amount: z.number().int().positive()
})

export const SchemaBalance = z.object({
	unique_id: z.number().int()
})
