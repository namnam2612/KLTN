import { ReactNode, useEffect, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import Login from './Login';
// import OTP from './OTP'; // COMMENTED - OTP flow disabled

type AuthPage = 'login' | 'authenticated';

interface AuthGuardProps {
  children: ReactNode;
}

export default function AuthGuard({ children }: AuthGuardProps) {
  const { isAuthenticated, isLoading } = useAuth();
  const [currentPage, setCurrentPage] = useState<AuthPage>('login');

  useEffect(() => {
    setCurrentPage(isAuthenticated ? 'authenticated' : 'login');
  }, [isAuthenticated]);

  if (isLoading) {
    return (
      <div className="flex min-h-screen bg-surface items-center justify-center">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
          <p className="text-on-surface mt-4">Đang tải...</p>
        </div>
      </div>
    );
  }

  if (currentPage === 'login') {
    return (
      <Login
        onLoginSuccess={() => {
          setCurrentPage('authenticated');
        }}
      />
    );
  }

  return <>{children}</>;
}