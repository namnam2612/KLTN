import express, { Request, Response } from 'express';
import queueService from '../services/queueService';
import jwtService, { DecodedToken } from '../services/jwtService';
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

/**
 * POST /api/auth/login
 * Authenticate user credentials and return JWT tokens
 */
router.post('/login', async (req: Request, res: Response) => {
  try {
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

    if (password.length < 6) {
      return res.status(400).json({
        success: false,
        message: 'Mật khẩu phải có ít nhất 6 ký tự'
      });
    }
    
    // Verify credentials against account table
    const verification = await accountService.verifyPassword(userIdentifier, password);
    if (!verification.ok || !verification.account) {
      return res.status(401).json({ success: false, message: 'Tên đăng nhập hoặc mật khẩu không đúng' });
    }

    const account = verification.account;
    const role = normalizeRole(account.role);

    // Check queue - CAN THIS USER ENTER?
    const queueCheck = await queueService.checkCanEnter(sessionId || '', userIdentifier);

    if (!queueCheck.canEnter) {
      // User is in queue - return JWT anyway so they can monitor position
      const { accessToken, refreshToken } = jwtService.generateTokenPair({
        userId: account.id,
        username: account.username,
        role
      });

      return res.status(200).json({
        success: true,
        message: 'Please wait in queue',
        canEnter: false,
        queuePosition: queueCheck.position,
        waitTime: queueCheck.waitTime,
        role,
        username: account.username,
        email: account.username,
        accessToken,
        refreshToken,
        sessionId
      });
    }

    // Add user to active session
    if (sessionId) {
      await queueService.addActiveUser(sessionId, userIdentifier);
    }

    // Generate JWT tokens
    const { accessToken, refreshToken } = jwtService.generateTokenPair({
      userId: account.id,
      username: account.username,
      role
    });

    console.log(`🔐 Login successful: username=${userIdentifier}, role=${role}`);

    return res.status(200).json({
      success: true,
      message: 'Login successful',
      canEnter: true,
      role,
      username: account.username,
      email: account.username,
      accessToken,
      refreshToken,
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
 * Verify access token and restore user session
 */
router.post('/verify', async (req: Request, res: Response) => {
  try {
    const { accessToken, sessionId } = req.body;
    
    if (!accessToken) {
      return res.status(401).json({ success: false, message: 'Access token không hợp lệ' });
    }

    // Verify JWT signature and expiry
    const decoded = jwtService.verifyAccessToken(accessToken) as DecodedToken | null;
    if (!decoded) {
      return res.status(401).json({ success: false, message: 'Token không hợp lệ hoặc đã hết hạn' });
    }

    // Get user from database to ensure they still exist
    const account = await accountService.findByUsername(decoded.username);
    if (!account) {
      return res.status(401).json({ success: false, message: 'User không tồn tại' });
    }

    // Check if user is still active in queue system (if sessionId provided)
    let isActive = true;
    if (sessionId) {
      isActive = await queueService.isUserActive(sessionId);
    }
    
    return res.status(200).json({
      success: true,
      message: 'Token verified',
      username: account.username,
      email: account.username,
      role: normalizeRole(account.role),
      userId: account.id,
      canEnter: isActive,
      sessionId
    });
  } catch (error) {
    console.error('Verify error:', error);
    return res.status(500).json({ success: false, message: 'Server error' });
  }
});

/**
 * POST /api/auth/refresh
 * Refresh access token using refresh token
 */
router.post('/refresh', async (req: Request, res: Response) => {
  try {
    const { refreshToken } = req.body;
    
    if (!refreshToken) {
      return res.status(401).json({ success: false, message: 'Refresh token không hợp lệ' });
    }

    // Verify JWT refresh token
    const decoded = jwtService.verifyRefreshToken(refreshToken) as DecodedToken | null;
    if (!decoded) {
      return res.status(401).json({ success: false, message: 'Refresh token không hợp lệ hoặc đã hết hạn' });
    }

    // Get user from database to ensure they still exist
    const account = await accountService.findByUsername(decoded.username);
    if (!account) {
      return res.status(401).json({ success: false, message: 'User không tồn tại' });
    }

    // Generate new token pair
    const { accessToken: newAccessToken, refreshToken: newRefreshToken } = jwtService.generateTokenPair({
      userId: account.id,
      username: account.username,
      role: normalizeRole(account.role)
    });

    console.log(`🔄 Token refreshed: username=${account.username}`);

    return res.status(200).json({
      success: true,
      message: 'Token refreshed',
      accessToken: newAccessToken,
      refreshToken: newRefreshToken,
      username: account.username,
      email: account.username,
      role: normalizeRole(account.role),
      userId: account.id
    });
  } catch (error) {
    console.error('Refresh error:', error);
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
