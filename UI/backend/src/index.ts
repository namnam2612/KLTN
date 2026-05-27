import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import authRoutes from './routes/auth';

dotenv.config();

const app = express();
const PORT = process.env.PORT || 3001;

// Middleware
app.use(cors());
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
  console.log(`🔐 Admin account: email=admin@gmail.com, password=admin`);
  console.log(`⏳ Queue Limit: Max 5 concurrent users`);
  console.log(`🌐 CORS enabled for http://localhost:3000`);
});
