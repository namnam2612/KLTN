import React, { createContext, useState, useEffect } from 'react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:3001';

interface User {
  email: string;
  role: 'admin' | 'student';
  isAuthenticated: boolean;
}

interface QueueStatus {
  queuePosition?: number;
  canEnter: boolean;
  waitTime?: number;
  message?: string;
}

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  sessionId: string;
  queueStatus: QueueStatus | null;
  login: (email: string, password: string) => Promise<{ success: boolean; message?: string; queueStatus?: QueueStatus }>;
  verifyOTP: (otp: string) => Promise<{ success: boolean; message?: string }>;
  logout: () => void;
  checkQueueStatus: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  // const [sessionEmail, setSessionEmail] = useState<string>(''); // COMMENTED - No longer used for OTP
  const [sessionId, setSessionId] = useState<string>('');
  const [queueStatus, setQueueStatus] = useState<QueueStatus | null>(null);

  // Generate session ID on mount
  useEffect(() => {
    const newSessionId = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    setSessionId(newSessionId);
    localStorage.setItem('sessionId', newSessionId);

    // Restore user session
    const storedUser = localStorage.getItem('user');
    if (storedUser) {
      const userData = JSON.parse(storedUser);
      setUser(userData);
      setIsAuthenticated(true);
    }
    setIsLoading(false);
  }, []);

  const checkQueueStatus = async () => {
    try {
      const response = await fetch(`${API_URL}/api/auth/queue-status?sessionId=${sessionId}`);
      const data = await response.json();
      
      if (data.success) {
        setQueueStatus({
          canEnter: data.stats.canEnter,
          queuePosition: data.userQueuePosition
        });
      }
    } catch (error) {
      console.error('Error checking queue status:', error);
    }
  };

  const login = async (email: string, password: string): Promise<{ success: boolean; message?: string; queueStatus?: QueueStatus }> => {
    try {
      // Check if admin account first (bypass all validation)
      if (email === 'admin@gmail.com' && password === 'admin') {
        const userData: User = {
          email: 'admin@gmail.com',
          role: 'admin',
          isAuthenticated: true
        };
        setUser(userData);
        setIsAuthenticated(true);
        localStorage.setItem('user', JSON.stringify(userData));
        localStorage.setItem('token', 'admin-token');
        setQueueStatus({ canEnter: true });
        return { success: true, message: 'Admin login successful', queueStatus: { canEnter: true } };
      }


      // Call backend to send OTP
      const response = await fetch(`${API_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, sessionId })
      });

      const data = await response.json();

      if (!response.ok) {
        return { success: false, message: data.message || 'Lỗi đăng nhập' };
      }

      // If user is in queue, show queue status
      if (!data.canEnter) {
        const qStatus: QueueStatus = {
          canEnter: false,
          queuePosition: data.queuePosition,
          waitTime: data.waitTime,
          message: `Bạn đang ở vị trí ${data.queuePosition} trong hàng đợi. Thời gian chờ dự kiến: ${data.waitTime} giây`
        };
        setQueueStatus(qStatus);
        return { success: true, message: qStatus.message, queueStatus: qStatus };
      }

      // ========== COMMENTED: OTP Flow ==========
      // setSessionEmail(email);
      
      // ========== DIRECT LOGIN (No OTP) ==========
      // No OTP needed - directly authenticate user from backend response
      const userData: User = {
        email: data.email,
        role: data.role,
        isAuthenticated: true
      };
      setUser(userData);
      setIsAuthenticated(true);
      localStorage.setItem('user', JSON.stringify(userData));
      localStorage.setItem('token', data.token);
      setQueueStatus({ canEnter: true });
      return { success: true, message: 'Login successful', queueStatus: { canEnter: true } };
    } catch (error) {
      console.error('Login error:', error);
      return { success: false, message: 'Không thể kết nối tới server. Đảm bảo backend đã chạy: npm start' };
    }
  };

  // ========== COMMENTED: OTP Verification (No longer needed) ==========
  // const verifyOTP = async (otp: string): Promise<{ success: boolean; message?: string }> => {
  //   try {
  //     const response = await fetch(`${API_URL}/api/auth/verify-otp`, {
  //       method: 'POST',
  //       headers: { 'Content-Type': 'application/json' },
  //       body: JSON.stringify({ email: sessionEmail, otp, sessionId })
  //     });
  //     const data = await response.json();
  //     if (!response.ok) {
  //       return { success: false, message: data.message || 'OTP không đúng hoặc đã hết hạn' };
  //     }
  //     const userData: User = {
  //       email: sessionEmail,
  //       role: data.role,
  //       isAuthenticated: true
  //     };
  //     setUser(userData);
  //     setIsAuthenticated(true);
  //     localStorage.setItem('user', JSON.stringify(userData));
  //     localStorage.setItem('token', data.token);
  //     setQueueStatus({ canEnter: true });
  //     return { success: true };
  //   } catch (error) {
  //     console.error('OTP verification error:', error);
  //     return { success: false, message: 'Không thể kết nối tới server. Đảm bảo backend đã chạy: npm start' };
  //   }
  // };

  // Placeholder for removed verifyOTP function - kept in context type for compatibility
  const verifyOTP = async (_otp: string): Promise<{ success: boolean; message?: string }> => {
    return { success: false, message: 'OTP verification is disabled' };
  };

  const logout = async () => {
    try {
      // Notify backend to remove from queue
      await fetch(`${API_URL}/api/auth/logout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sessionId })
      });
    } catch (error) {
      console.error('Logout error:', error);
    }

    setUser(null);
    setIsAuthenticated(false);
    // setSessionEmail(''); // COMMENTED - sessionEmail no longer used
    setQueueStatus(null);
    localStorage.removeItem('user');
    localStorage.removeItem('token');
  };

  return (
    <AuthContext.Provider value={{ user, isAuthenticated, isLoading, sessionId, queueStatus, login, verifyOTP, logout, checkQueueStatus }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = React.useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
}