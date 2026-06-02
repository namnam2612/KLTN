import { pool } from './db';
import bcrypt from 'bcryptjs';

export interface Account {
  id: number;
  username: string;
  password: string;
  role: string;
}

export const findByUsername = async (username: string): Promise<Account | null> => {
  const [rows] = await pool.execute('SELECT id, username, password, role FROM account WHERE username = ? LIMIT 1', [username]);
  const results = rows as any[];
  if (results.length === 0) return null;
  return results[0] as Account;
};

export const verifyPassword = async (username: string, plainPassword: string): Promise<{ ok: boolean; account?: Account }> => {
  const account = await findByUsername(username);
  if (!account) return { ok: false };

  // If password stored as bcrypt hash, compare; otherwise compare directly
  try {
    const isHash = account.password.startsWith('$2a$') || account.password.startsWith('$2b$') || account.password.startsWith('$2y$');
    if (isHash) {
      const match = await bcrypt.compare(plainPassword, account.password);
      return { ok: match, account: match ? account : undefined };
    }
  } catch (err) {
    // fallthrough to plain compare
  }

  if (account.password === plainPassword) {
    return { ok: true, account };
  }

  return { ok: false };
};

export const createAccount = async (username: string, plainPassword: string, role = 'user'): Promise<Account> => {
  const saltRounds = parseInt(process.env.BCRYPT_SALT_ROUNDS || '10', 10);
  const hash = await bcrypt.hash(plainPassword, saltRounds);
  console.log(`Creating account: username=${username}, role=${role} (type: ${typeof role})`);
  const [result] = await pool.execute('INSERT INTO account (username, password, role) VALUES (?, ?, ?)', [username, hash, role]);
  // @ts-ignore
  const insertId = result.insertId || (result as any)?.insertId;
  return {
    id: insertId,
    username,
    password: hash,
    role,
  } as Account;
};

export default { findByUsername, verifyPassword, createAccount };
