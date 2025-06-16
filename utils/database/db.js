import mysql from 'mysql2/promise'
import fs from 'fs/promises'
import path from 'path'
import { config } from 'dotenv'

config()
const { DB_USER, DB_PASS } = process.env

const db = mysql.createPool({
	host: 'localhost',
	user: DB_USER,
	password: DB_PASS,
	database: 'api',
	waitForConnections: true,
	multipleStatements: true,
	// connectionLimit: 10,
	// queueLimit: 0
})

export const init_tables = async () => {
	const schemaPath = path.resolve('./utils/database/table_schemas.sql')
	const schema = await fs.readFile(schemaPath, 'utf8')

	const conn = await db.getConnection()
	try {
		await conn.query(schema)
		console.log('✅ tables initialized')
	} finally {
		conn.release()
	}
}

export default db
