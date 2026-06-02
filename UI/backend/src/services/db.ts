import mysql from 'mysql2/promise';
import { getNumberEnv, getRequiredEnv } from '../config/env';

const DB_HOST = getRequiredEnv('DB_HOST');
const DB_PORT = getNumberEnv('DB_PORT');
const DB_USER = getRequiredEnv('DB_USER');
const DB_PASSWORD = getRequiredEnv('DB_PASSWORD');
const DB_NAME = getRequiredEnv('DB_NAME');

export const pool = mysql.createPool({
  host: DB_HOST,
  port: DB_PORT,
  user: DB_USER,
  password: DB_PASSWORD,
  database: DB_NAME,
  waitForConnections: true,
  connectionLimit: 10,
  queueLimit: 0,
});

export default pool;
