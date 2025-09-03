import express from 'express'
import { config } from 'dotenv'

import { db, init_tables } from './db.js'
import routerEquity from './routes/equity.js'

const app = express()
app.use(express.json())
config()
const PORT = process.env.PORT

app.use('/equity', routerEquity)

app.listen( PORT, async () => {
	try {
		const conn = await db.getConnection()
		conn.release()
		console.log(' DB connected')
		await init_tables()
		console.log(` live on port ${PORT}`)
	} catch (err) {
		console.error(' DB connection failed:', err)
		process.exit(1)
	}
})