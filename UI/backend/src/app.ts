import express from 'express';
import cors from 'cors';
import authRoutes from './routes/auth';
import { getOptionalEnv } from './config/env';

const app = express();
const CORS_ORIGIN = getOptionalEnv('CORS_ORIGIN', 'http://localhost:3000');

app.use(cors({ origin: CORS_ORIGIN }));
app.use(express.json());

app.use('/api/auth', authRoutes);

app.get('/health', (_req, res) => {
  res.json({ status: 'OK', message: 'Auth server is running' });
});

export { CORS_ORIGIN };
export default app;
