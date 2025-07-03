import mysql from 'mysql2/promise'
import fs from 'fs/promises'
import path from 'path'
import { config } from 'dotenv'

config()
const { DB_USER, DB_PASS, DB_URL, DB_PORT, DB_NAME } = process.env

export const db = mysql.createPool({
	host: DB_URL,
	port: DB_PORT,
	user: DB_USER,
	password: DB_PASS,
	database: DB_NAME,
	waitForConnections: true,
	multipleStatements: true,
	supportBigNumbers: true,
	bigNumberStrings: true
	// connectionLimit: 10,
	// queueLimit: 0
})

export const init_tables = async () => {
	const schemaPath = path.resolve('./table_schemas.sql')
	const schema = await fs.readFile(schemaPath, 'utf8')

	const conn = await db.getConnection()
	try {
		await conn.query(schema)
		console.log('✅ tables initialized')
	} finally {
		conn.release()
	}
}
