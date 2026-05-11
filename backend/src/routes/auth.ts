import express, { Request, Response } from 'express';
import redis from 'redis';
import queueService from '../services/queueService';
import dotenv from 'dotenv';
import accountService from '../services/accountService';

dotenv.config();

const router = express.Router();

const normalizeRole = (rawRole: unknown): 'admin' | 'user' => {
  if (typeof rawRole === 'string') {
    const normalized = rawRole.trim().toLowerCase();
    if (normalized === 'admin') return 'admin';
  }
  if (rawRole === 1 || rawRole === '1') return 'admin';
  return 'user';
};

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
    // accept `username` (preferred) or `email` for backward-compatibility
    const { username, email, password, sessionId } = req.body;
    const userIdentifier = username || email;

    // Validate inputs
    if (!userIdentifier) {
      return res.status(400).json({
        success: false,
        message: 'Username hoặc email là bắt buộc'
      });
    }

    if (!password) {
      return res.status(400).json({
        success: false,
        message: 'Mật khẩu là bắt buộc'
      });
    }

    // Validate password length
    if (password.length < 6) {
      return res.status(400).json({
        success: false,
        message: 'Mật khẩu phải có ít nhất 6 ký tự'
      });
    }

    // ========== COMMENTED: OTP Flow ==========
    // const otp = generateOTP();
    // await redisClient.setEx(`otp:${email}`, 60, otp);
    // await redisClient.setEx(`password:${email}`, 60, password);
    // await sendOTP(email, otp);
    
    // Verify credentials against `account` table
    const verification = await accountService.verifyPassword(userIdentifier, password);
    if (!verification.ok || !verification.account) {
      return res.status(401).json({ success: false, message: 'Tên đăng nhập hoặc mật khẩu không đúng' });
    }

    const role = normalizeRole(verification.account.role);
    const token = `token-${userIdentifier}-${Date.now()}`;

    // Check queue - CAN THIS USER ENTER?
    const queueCheck = await queueService.checkCanEnter(sessionId || '', userIdentifier);

    if (!queueCheck.canEnter) {
      // User is in queue
      return res.status(200).json({
        success: true,
        message: 'Please wait in queue',
        canEnter: false,
        queuePosition: queueCheck.position,
        waitTime: queueCheck.waitTime,
        role,
        token,
        username: verification.account.username,
        sessionId
      });
    }

    // Add user to active session
    if (sessionId) {
      await queueService.addActiveUser(sessionId, userIdentifier);
    }

    console.log(`🔐 Login attempt: username=${userIdentifier}, role from DB=${verification.account.role}, returning role=${role}`);

    return res.status(200).json({
      success: true,
      message: 'Login successful',
      canEnter: true,
      role: role,
      token: token,
      username: verification.account.username,
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
 * POST /api/auth/register
 * Register new account
 */
router.post('/register', async (req: Request, res: Response) => {
  try {
    const { username, password, confirmPassword, role } = req.body;

    if (!username || !password || !confirmPassword) {
      return res.status(400).json({ success: false, message: 'Username và mật khẩu là bắt buộc' });
    }

    if (password !== confirmPassword) {
      return res.status(400).json({ success: false, message: 'Mật khẩu và xác nhận mật khẩu không khớp' });
    }

    if (password.length < 6) {
      return res.status(400).json({ success: false, message: 'Mật khẩu phải có ít nhất 6 ký tự' });
    }

    const existing = await accountService.findByUsername(username);
    if (existing) {
      return res.status(409).json({ success: false, message: 'Username đã tồn tại' });
    }

    const acct = await accountService.createAccount(username, password, role || 'user');
    console.log(`✅ Account created: username=${acct.username}, role=${acct.role}`);

    return res.status(201).json({ success: true, message: 'Đăng ký thành công', account: { id: acct.id, username: acct.username, role: acct.role } });
  } catch (error) {
    console.error('Register error:', error);
    return res.status(500).json({ success: false, message: 'Server error' });
  }
});

/**
 * POST /api/auth/verify
 * Verify token and restore user session
 */
router.post('/verify', async (req: Request, res: Response) => {
  try {
    const { token, sessionId } = req.body;
    
    if (!token || !sessionId) {
      return res.status(401).json({ success: false, message: 'Token hoặc sessionId không hợp lệ' });
    }

    // Simple token format: token-username-timestamp
    // Extract username from token
    const parts = token.split('-');
    if (parts.length < 3) {
      return res.status(401).json({ success: false, message: 'Token không hợp lệ' });
    }

    const username = parts.slice(1, -1).join('-'); // Join in case username has hyphens

    // Verify token exists and get user from database
    const account = await accountService.findByUsername(username);
    if (!account) {
      return res.status(401).json({ success: false, message: 'User không tồn tại' });
    }

    // Check if user is still active in queue system
    const isActive = await queueService.isUserActive(sessionId);
    
    return res.status(200).json({
      success: true,
      message: 'Token verified',
      username: account.username,
      email: account.username,
      role: normalizeRole(account.role),
      token: token,
      canEnter: isActive || false,
      sessionId
    });
  } catch (error) {
    console.error('Verify error:', error);
    return res.status(500).json({ success: false, message: 'Server error' });
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
