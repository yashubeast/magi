import { z } from 'zod'

export const SchemaEval = z.object({
	user_id: z.number().int(),
	server_id: z.number().int(),
	message_length: z.number().int(),
	timestamp: z.coerce.date()
})

export const SchemaTransferCoin = z.object({
	sender_id: z.number().int(),
	receiver_id: z.number().int(),
	amount: z.number().int().positive()
})

export const SchemaBalance = z.object({
	unique_id: z.number().int()
})
