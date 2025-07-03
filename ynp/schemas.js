import { z } from 'zod'

export const SchemaEval = z.object({
	user_id: z.string(),
	message_id: z.string(),
	message_length: z.number().int(),
	timestamp: z.string()
})

export const SchemaDel = z.object({
	message_id: z.string()
})

export const SchemaTransferCoin = z.object({
	sender_id: z.string(),
	receiver_id: z.string(),
	amount: z.number().int().positive()
})

export const SchemaBalance = z.object({
	user_id: z.string()
})
