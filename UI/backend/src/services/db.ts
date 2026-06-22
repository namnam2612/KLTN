import mysql from 'mysql2/promise';
import { getNumberEnv, getOptionalEnv, getRequiredEnv } from '../config/env';

const DB_HOST = getRequiredEnv('DB_HOST');
const DB_PORT = getNumberEnv('DB_PORT');
const DB_USER = getRequiredEnv('DB_USER');
const DB_PASSWORD = getRequiredEnv('DB_PASSWORD');
const DB_NAME = getRequiredEnv('DB_NAME');
const DB_SSL = getOptionalEnv('DB_SSL', 'false').toLowerCase() === 'true';

export const pool = mysql.createPool({
  host: DB_HOST,
  port: DB_PORT,
  user: DB_USER,
  password: DB_PASSWORD,
  database: DB_NAME,
  ssl: DB_SSL ? { rejectUnauthorized: true } : undefined,
  waitForConnections: true,
  connectionLimit: 10,
  queueLimit: 0,
});

export default pool;
