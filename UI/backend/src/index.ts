import express from 'express';
import cors from 'cors';
import authRoutes from './routes/auth';
import { getNumberEnv, getOptionalEnv } from './config/env';

const app = express();
const PORT = getNumberEnv('PORT', 3001);
const CORS_ORIGIN = getOptionalEnv('CORS_ORIGIN', 'http://localhost:3000');

// Middleware
app.use(cors({ origin: CORS_ORIGIN }));
app.use(express.json());

// Routes
app.use('/api/auth', authRoutes);

// Health check
app.get('/health', (_req, res) => {
  res.json({ status: 'OK', message: 'Auth server is running' });
});

// Start server
app.listen(PORT, () => {
  console.log(`🚀 Auth server running on port ${PORT}`);
  console.log(`⏳ Queue service enabled`);
  console.log(`🌐 CORS enabled for ${CORS_ORIGIN}`);
});
