import jwt from 'jsonwebtoken';
import dotenv from 'dotenv';
import type { SignOptions } from 'jsonwebtoken';

dotenv.config();

const JWT_SECRET = process.env.JWT_SECRET || 'default_secret_key_change_in_production';
const ACCESS_TOKEN_EXPIRES_IN: SignOptions['expiresIn'] = (process.env.JWT_ACCESS_TOKEN_EXPIRES_IN || '15m') as SignOptions['expiresIn'];
const REFRESH_TOKEN_EXPIRES_IN: SignOptions['expiresIn'] = (process.env.JWT_REFRESH_TOKEN_EXPIRES_IN || '7d') as SignOptions['expiresIn'];

export interface TokenPayload {
  userId: number;
  username: string;
  role: 'admin' | 'user';
  type: 'access' | 'refresh';
}

export interface DecodedToken {
  userId: number;
  username: string;
  role: 'admin' | 'user';
  type: 'access' | 'refresh';
  iat: number;
  exp: number;
}

export const generateAccessToken = (payload: Omit<TokenPayload, 'type'>): string => {
  return jwt.sign(
    { ...payload, type: 'access' },
    JWT_SECRET,
    { expiresIn: ACCESS_TOKEN_EXPIRES_IN }
  );
};

export const generateRefreshToken = (payload: Omit<TokenPayload, 'type'>): string => {
  return jwt.sign(
    { ...payload, type: 'refresh' },
    JWT_SECRET,
    { expiresIn: REFRESH_TOKEN_EXPIRES_IN }
  );
};

export const generateTokenPair = (payload: Omit<TokenPayload, 'type'>) => {
  const accessToken = generateAccessToken(payload);
  const refreshToken = generateRefreshToken(payload);
  return { accessToken, refreshToken };
};

export const verifyAccessToken = (token: string): DecodedToken | null => {
  try {
    const decoded = jwt.verify(token, JWT_SECRET) as DecodedToken;
    if (decoded.type !== 'access') {
      return null;
    }
    return decoded;
  } catch (error) {
    return null;
  }
};

export const verifyRefreshToken = (token: string): DecodedToken | null => {
  try {
    const decoded = jwt.verify(token, JWT_SECRET) as DecodedToken;
    if (decoded.type !== 'refresh') {
      return null;
    }
    return decoded;
  } catch (error) {
    return null;
  }
};

export const decodeToken = (token: string): DecodedToken | null => {
  try {
    const decoded = jwt.decode(token) as DecodedToken | null;
    return decoded;
  } catch (error) {
    return null;
  }
};

export const isTokenExpired = (token: string): boolean => {
  const decoded = decodeToken(token);
  if (!decoded) return true;
  const now = Math.floor(Date.now() / 1000);
  return decoded.exp <= now;
};

export const getTokenExpiresIn = (token: string): number | null => {
  const decoded = decodeToken(token);
  if (!decoded) return null;
  const now = Math.floor(Date.now() / 1000);
  return decoded.exp - now; // seconds remaining
};

export default {
  generateAccessToken,
  generateRefreshToken,
  generateTokenPair,
  verifyAccessToken,
  verifyRefreshToken,
  decodeToken,
  isTokenExpired,
  getTokenExpiresIn,
};
