import React, { createContext, useState, useEffect, useCallback } from 'react';
import { AUTH_API_URL } from '../config/api';

interface User {
  email: string;
  role: 'admin' | 'user';
  isAuthenticated: boolean;
  userId?: number;
}

const USER_ID_STORAGE_KEY = 'chatUserId';
const USER_STORAGE_KEY = 'user';

function decodeJwtPayload(token: string): { userId?: number; email?: string; username?: string; role?: 'admin' | 'user' } | null {
  try {
    const parts = token.split('.');
    if (parts.length !== 3) return null;

    const normalized = parts[1].replace(/-/g, '+').replace(/_/g, '/');
    const padded = normalized + '='.repeat((4 - (normalized.length % 4)) % 4);
    const payload = JSON.parse(atob(padded));
    return payload;
  } catch {
    return null;
  }
}

function parseStoredUser(): User | null {
  const storedUser = localStorage.getItem(USER_STORAGE_KEY);
  if (!storedUser) return null;

  try {
    return JSON.parse(storedUser) as User;
  } catch {
    return null;
  }
}

function extractUserIdFromToken(token: string): number | undefined {
  const decoded = decodeJwtPayload(token);
  return decoded?.userId;
}

function normalizeUserData(data: any, fallbackEmail?: string): User {
  return {
    email: data.email || data.username || fallbackEmail || 'User',
    role: data.role === 'admin' ? 'admin' : 'user',
    isAuthenticated: true,
    userId: typeof data.userId === 'number' ? data.userId : Number(data.userId) || undefined
  };
}

interface QueueStatus {
  queuePosition?: number;
  canEnter: boolean;
  waitTime?: number;
  message?: string;
}

interface AuthContextType {
  user: User | null;
  chatUserId: string;
  isAuthenticated: boolean;
  isLoading: boolean;
  sessionId: string;
  queueStatus: QueueStatus | null;
  login: (email: string, password: string) => Promise<{ success: boolean; message?: string; queueStatus?: QueueStatus }>;
  logout: () => void;
  checkQueueStatus: () => Promise<void>;
  register: (username: string, password: string, confirmPassword: string) => Promise<{ success: boolean; message?: string }>;
  refreshAccessToken: () => Promise<boolean>;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [sessionId, setSessionId] = useState<string>('');
  const [queueStatus, setQueueStatus] = useState<QueueStatus | null>(null);
  const chatUserId = user?.userId ? String(user.userId) : '';

  const persistUser = (userData: User) => {
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(userData));
    if (typeof userData.userId === 'number' && Number.isFinite(userData.userId)) {
      localStorage.setItem(USER_ID_STORAGE_KEY, String(userData.userId));
    } else {
      localStorage.removeItem(USER_ID_STORAGE_KEY);
    }
  };

  // Helper: Check if access token is still valid
  const isAccessTokenValid = useCallback((): boolean => {
    const accessToken = localStorage.getItem('accessToken');
    if (!accessToken) return false;

    try {
      // Decode JWT to check expiry
      const parts = accessToken.split('.');
      if (parts.length !== 3) return false;

      const decoded = JSON.parse(atob(parts[1]));
      const now = Math.floor(Date.now() / 1000);
      return decoded.exp > now;
    } catch (error) {
      console.error('Error checking token validity:', error);
      return false;
    }
  }, []);

  // Helper: Refresh access token using refresh token
  const refreshAccessToken = useCallback(async (): Promise<boolean> => {
    try {
      const refreshToken = localStorage.getItem('refreshToken');
      if (!refreshToken) {
        console.log('No refresh token available');
        return false;
      }

      const response = await fetch(`${AUTH_API_URL}/api/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refreshToken })
      });

      const data = await response.json();

      if (!data.success || !data.accessToken) {
        console.log('Token refresh failed:', data.message);
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
        localStorage.removeItem('user');
        return false;
      }

      // Store new tokens
      localStorage.setItem('accessToken', data.accessToken);
      if (data.refreshToken) {
        localStorage.setItem('refreshToken', data.refreshToken);
      }

      console.log('Access token refreshed successfully');
      return true;
    } catch (error) {
      console.error('Token refresh error:', error);
      return false;
    }
  }, []);

  // On mount: Try to restore session if tokens exist and valid
  useEffect(() => {
    const newSessionId = `session-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    setSessionId(newSessionId);
    localStorage.setItem('sessionId', newSessionId);

    const verifySession = async () => {
      const accessToken = localStorage.getItem('accessToken');
      const storedUser = parseStoredUser();
      
      if (accessToken && storedUser) {
        try {
          // Check if access token is still valid
          if (isAccessTokenValid()) {
            if (storedUser.userId) {
              console.log('Session restored from valid token, role:', storedUser.role);
              setUser(storedUser);
              setIsAuthenticated(true);
              persistUser(storedUser);
            } else {
              const fallbackUserId = extractUserIdFromToken(accessToken);

              if (fallbackUserId) {
                const userData: User = {
                  ...storedUser,
                  userId: fallbackUserId,
                  isAuthenticated: true,
                };
                persistUser(userData);
                setUser(userData);
                setIsAuthenticated(true);
              } else {
                const response = await fetch(`${AUTH_API_URL}/api/auth/verify`, {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ accessToken, sessionId: newSessionId })
                });

                const data = await response.json();
                if (data.success && data.userId) {
                  const userData = normalizeUserData(data, storedUser.email);
                  persistUser(userData);
                  setUser(userData);
                  setIsAuthenticated(true);
                } else {
                  localStorage.removeItem(USER_STORAGE_KEY);
                  localStorage.removeItem('accessToken');
                  localStorage.removeItem('refreshToken');
                }
              }
            }
          } else {
            // Access token expired, try to refresh
            console.log('Access token expired, attempting refresh...');
            const refreshToken = localStorage.getItem('refreshToken');
            
            if (refreshToken) {
              const response = await fetch(`${AUTH_API_URL}/api/auth/refresh`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refreshToken })
              });

              const data = await response.json();

              if (data.success && data.accessToken) {
                // New tokens received
                localStorage.setItem('accessToken', data.accessToken);
                if (data.refreshToken) {
                  localStorage.setItem('refreshToken', data.refreshToken);
                }

                const userData = normalizeUserData(data, data.email || data.username);
                console.log('Session restored after token refresh');
                setUser(userData);
                setIsAuthenticated(true);
                persistUser(userData);
              } else {
                // Refresh failed, clear storage
                console.log('Token refresh failed during session restore');
                localStorage.removeItem(USER_STORAGE_KEY);
                localStorage.removeItem('accessToken');
                localStorage.removeItem('refreshToken');
              }
            } else {
              // No refresh token, clear storage
              localStorage.removeItem(USER_STORAGE_KEY);
              localStorage.removeItem('accessToken');
            }
          }
        } catch (error) {
          console.error('Session verification error:', error);
          localStorage.removeItem(USER_STORAGE_KEY);
          localStorage.removeItem('accessToken');
          localStorage.removeItem('refreshToken');
        }
      }
      setIsLoading(false);
    };

    verifySession();
  }, [isAccessTokenValid]);

  const checkQueueStatus = async () => {
    try {
      const response = await fetch(`${AUTH_API_URL}/api/auth/queue-status?sessionId=${sessionId}`);
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
      const response = await fetch(`${AUTH_API_URL}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, sessionId })
      });

      const data = await response.json();

      if (!response.ok) {
        return { success: false, message: data.message || 'Lỗi đăng nhập' };
      }

      if (!data.success || !data.accessToken) {
        return { success: false, message: data.message || 'Lỗi đăng nhập' };
      }

      const userEmail = data.email || data.username || email;
      const userRole = (data.role === 'admin' ? 'admin' : 'user') as 'admin' | 'user';
      
      const userData: User = {
        email: userEmail,
        role: userRole,
        isAuthenticated: true,
        userId: data.userId
      };

      // Store tokens and user data
      localStorage.setItem('accessToken', data.accessToken);
      if (data.refreshToken) {
        localStorage.setItem('refreshToken', data.refreshToken);
      }
      persistUser(userData);

      setUser(userData);
      setIsAuthenticated(true);

      console.log('Login successful, role:', userRole);

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

  const register = async (username: string, password: string, confirmPassword: string): Promise<{ success: boolean; message?: string }> => {
    try {
      const response = await fetch(`${AUTH_API_URL}/api/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password, confirmPassword })
      });

      const data = await response.json();
      console.log('Register response:', data);
      
      if (!response.ok) {
        return { success: false, message: data.message || 'Đăng ký không thành công' };
      }

      return { success: true, message: data.message || 'Đăng ký thành công' };
    } catch (error) {
      console.error('Register error:', error);
      return { success: false, message: 'Không thể kết nối tới server' };
    }
  };

  const logout = async () => {
    try {
      console.log('Calling logout API with sessionId=', sessionId);
      await fetch(`${AUTH_API_URL}/api/auth/logout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sessionId })
      }).then(res => console.log('Logout response status:', res.status)).catch(err => console.error('Logout request failed:', err));
    } catch (error) {
      console.error('Logout error:', error);
    }

    setUser(null);
    setIsAuthenticated(false);
    setQueueStatus(null);
    localStorage.removeItem(USER_STORAGE_KEY);
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem(USER_ID_STORAGE_KEY);
  };

  return (
    <AuthContext.Provider value={{ user, chatUserId, isAuthenticated, isLoading, sessionId, queueStatus, login, logout, checkQueueStatus, register, refreshAccessToken }}>
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
