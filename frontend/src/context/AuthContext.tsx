import React, { createContext, useState, useEffect } from 'react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:3001';

interface User {
  email: string;
  role: 'admin' | 'user';
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
  register: (username: string, password: string, confirmPassword: string, role?: string) => Promise<{ success: boolean; message?: string }>;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  // const [sessionEmail, setSessionEmail] = useState<string>(''); // COMMENTED - No longer used for OTP
  const [sessionId, setSessionId] = useState<string>('');
  const [queueStatus, setQueueStatus] = useState<QueueStatus | null>(null);

  // Generate session ID on mount and verify existing token
  useEffect(() => {
    const newSessionId = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    setSessionId(newSessionId);
    localStorage.setItem('sessionId', newSessionId);

    // Try to restore user session from token
    const verifySession = async () => {
      const token = localStorage.getItem('token');
      const storedUser = localStorage.getItem('user');
      
      if (token && storedUser) {
        try {
          // Verify token with backend
          const response = await fetch(`${API_URL}/api/auth/verify`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token, sessionId: newSessionId })
          });

          const data = await response.json();
          if (data.success && data.role) {
            // Token is valid, restore user with data from server
            const normalizedRole = data.role.toString().trim().toLowerCase();
            const userRole = (normalizedRole === 'admin' ? 'admin' : 'user') as 'admin' | 'user';
            const userData: User = {
              email: data.email || data.username,
              role: userRole,
              isAuthenticated: true
            };
            console.log('Session restored with role:', userRole);
            setUser(userData);
            setIsAuthenticated(true);
            localStorage.setItem('user', JSON.stringify(userData));
          } else {
            // Token is invalid, clear storage
            console.log('Token verification failed');
            localStorage.removeItem('user');
            localStorage.removeItem('token');
          }
        } catch (error) {
          console.error('Session verification error:', error);
          localStorage.removeItem('user');
          localStorage.removeItem('token');
        }
      }
      setIsLoading(false);
    };

    verifySession();
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

      // ========== DIRECT LOGIN (No OTP) ==========
      // No OTP needed - directly authenticate user from backend response
      const userEmail = data.username || data.email || email;
      const normalizedRole = data.role?.toString().trim().toLowerCase();
      const userRole = (normalizedRole === 'admin' ? 'admin' : 'user') as 'admin' | 'user';
      console.log('Login response role:', data.role, 'Converted role:', userRole);
      
      const userData: User = {
        email: userEmail,
        role: userRole,
        isAuthenticated: true
      };
      setUser(userData);
      setIsAuthenticated(true);
      localStorage.setItem('user', JSON.stringify(userData));
      if (data.token) {
        localStorage.setItem('token', data.token);
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

      setQueueStatus({ canEnter: true });
      return { success: true, message: 'Login successful', queueStatus: { canEnter: true } };
    } catch (error) {
      console.error('Login error:', error);
      return { success: false, message: 'Không thể kết nối tới server. Đảm bảo backend đã chạy: npm start' };
    }
  };

  const register = async (username: string, password: string, confirmPassword: string, role = 'user'): Promise<{ success: boolean; message?: string }> => {
    try {
      const response = await fetch(`${API_URL}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, confirmPassword, role })
      });

      const data = await response.json();
      console.log('Register response:', data);
      
      if (!response.ok) {
        return { success: false, message: data.message || 'Đăng ký không thành công' };
      }

      // Auto-login after register
      console.log('Auto-login with username:', username, 'role selected:', role);
      await login(username, password);
      return { success: true, message: data.message || 'Đăng ký thành công' };
    } catch (error) {
      console.error('Register error:', error);
      return { success: false, message: 'Không thể kết nối tới server' };
    }
  };
  // Placeholder for removed verifyOTP function - kept in context type for compatibility
  const verifyOTP = async (_otp: string): Promise<{ success: boolean; message?: string }> => {
    return { success: false, message: 'OTP verification is disabled' };
  };

  const logout = async () => {
    try {
      console.log('Calling logout API with sessionId=', sessionId);
      // Notify backend to remove from queue
      await fetch(`${API_URL}/api/auth/logout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sessionId })
      }).then(res => console.log('Logout response status:', res.status)).catch(err => console.error('Logout request failed:', err));
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
    <AuthContext.Provider value={{ user, isAuthenticated, isLoading, sessionId, queueStatus, login, verifyOTP, logout, checkQueueStatus, register }}>
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