import express, { Request, Response } from 'express';
import redis from 'redis';
import queueService from '../services/queueService';
import dotenv from 'dotenv';

dotenv.config();

const router = express.Router();

const redisClient = redis.createClient({
  socket: {
    host: process.env.REDIS_HOST || 'localhost',
    port: parseInt(process.env.REDIS_PORT || '6379'),
  },
});

redisClient.on('error', (err) => console.log('Redis Client Error', err));
redisClient.connect();

// ========== COMMENTED: OTP Generation (No longer used) ==========
// const generateOTP = (): string => {
//   return Math.floor(100000 + Math.random() * 900000).toString();
// };

// ========== COMMENTED: OTP Sending (No longer used) ==========
// const sendOTP = async (email: string, otp: string): Promise<void> => {
//   console.log(`📧 OTP sent to ${email}: ${otp}`);
// };

/**
 * POST /api/auth/login
 * Send OTP to user email
 */
router.post('/login', async (req: Request, res: Response) => {
  try {
    const { email, password, sessionId } = req.body;

    // Validate inputs
    if (!email) {
      return res.status(400).json({
        success: false,
        message: 'Email là bắt buộc'
      });
    }

    if (!password) {
      return res.status(400).json({
        success: false,
        message: 'Mật khẩu là bắt buộc'
      });
    }

    // Check if admin account (bypass all validation)
    if (email === 'admin@gmail.com' && password === 'admin') {
      // Add admin to active users immediately
      if (sessionId) {
        await queueService.addActiveUser(sessionId, email);
      }

      return res.status(200).json({
        success: true,
        message: 'Admin login successful',
        role: 'admin',
        token: 'admin-token-' + Date.now(),
        canEnter: true
      });
    }

    // Validate password
    if (password.length < 6) {
      return res.status(400).json({
        success: false,
        message: 'Mật khẩu phải có ít nhất 6 ký tự'
      });
    }

    // Check queue - CAN THIS USER ENTER?
    const queueCheck = await queueService.checkCanEnter(sessionId || '', email);

    if (!queueCheck.canEnter) {
      // User is in queue
      return res.status(200).json({
        success: true,
        message: 'Please wait in queue',
        canEnter: false,
        queuePosition: queueCheck.position,
        waitTime: queueCheck.waitTime,
        sessionId
      });
    }

    // ========== COMMENTED: OTP Flow ==========
    // const otp = generateOTP();
    // await redisClient.setEx(`otp:${email}`, 60, otp);
    // await redisClient.setEx(`password:${email}`, 60, password);
    // await sendOTP(email, otp);
    
    // ========== DIRECT LOGIN (No OTP) ==========
    // Add user to active session
    if (sessionId) {
      await queueService.addActiveUser(sessionId, email);
    }

    // Determine user role
    const role = 'user'; // All non-admin users are 'user' role

    // Create token
    const token = `token-${email}-${Date.now()}`;

    return res.status(200).json({
      success: true,
      message: 'Login successful',
      canEnter: true,
      role: role,
      token: token,
      email: email,
      sessionId
    });
  } catch (error) {
    console.error('Login error:', error);
    return res.status(500).json({
      success: false,
      message: 'Server error'
    });
  }
});

// ========== COMMENTED: OTP Verification Route ==========
// No longer needed - users authenticate directly on login
// router.post('/verify-otp', async (req: Request, res: Response) => {
//   try {
//     const { email, otp, sessionId } = req.body;
//     if (!email || !otp) {
//       return res.status(400).json({
//         success: false,
//         message: 'Email and OTP are required'
//       });
//     }
//     const storedOTP = await redisClient.get(`otp:${email}`);
//     if (!storedOTP) {
//       return res.status(401).json({
//         success: false,
//         message: 'OTP expired or not found'
//       });
//     }
//     if (storedOTP !== otp) {
//       return res.status(401).json({
//         success: false,
//         message: 'OTP is incorrect'
//       });
//     }
//     await redisClient.del(`otp:${email}`);
//     await redisClient.del(`password:${email}`);
//     if (sessionId) {
//       await queueService.addActiveUser(sessionId, email);
//     }
//     const role = email.startsWith('admin') ? 'admin' : 'user';
//     const token = `token-${email}-${Date.now()}`;
//     return res.status(200).json({
//       success: true,
//       message: 'OTP verified successfully',
//       role: role,
//       token: token,
//       email: email,
//       sessionId
//     });
//   } catch (error) {
//     console.error('OTP verification error:', error);
//     return res.status(500).json({
//       success: false,
//       message: 'Server error'
//     });
//   }
// });

/**
 * POST /api/auth/logout
 * Logout user and remove from active
 */
router.post('/logout', async (req: Request, res: Response) => {
  try {
    const { sessionId } = req.body;

    if (sessionId) {
      await queueService.removeActiveUser(sessionId);
    }

    return res.status(200).json({
      success: true,
      message: 'Logged out successfully'
    });
  } catch (error) {
    console.error('Logout error:', error);
    return res.status(500).json({
      success: false,
      message: 'Server error'
    });
  }
});

/**
 * GET /api/auth/queue-status
 * Get current queue status
 */
router.get('/queue-status', async (req: Request, res: Response) => {
  try {
    const { sessionId } = req.query;
    
    const stats = await queueService.getStats();
    let userPosition = null;

    if (sessionId) {
      const isActive = await queueService.isUserActive(sessionId as string);
      if (!isActive) {
        userPosition = await queueService.getUserQueuePosition(sessionId as string);
      }
    }

    return res.status(200).json({
      success: true,
      stats,
      userQueuePosition: userPosition
    });
  } catch (error) {
    console.error('Queue status error:', error);
    return res.status(500).json({
      success: false,
      message: 'Server error'
    });
  }
});

export default router;
