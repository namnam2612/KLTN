import { ReactNode, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import Login from './Login';
// import OTP from './OTP'; // COMMENTED - OTP flow disabled

type AuthPage = 'login' | 'otp' | 'authenticated';

interface AuthGuardProps {
  children: ReactNode;
}

export default function AuthGuard({ children }: AuthGuardProps) {
  const { isAuthenticated, isLoading } = useAuth();
  const [currentPage, setCurrentPage] = useState<AuthPage>('login');

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

  if (!isAuthenticated) {
    if (currentPage === 'login') {
      return (
        <Login
          onLoginSuccess={() => {
            // ========== COMMENTED: OTP Flow (No longer needed) ==========
            // setCurrentPage(user?.role === 'admin' ? 'authenticated' : 'otp');
            
            // ========== DIRECT AUTH (No OTP) ==========
            // All users (admin or regular) go directly to chatbot
            setCurrentPage('authenticated');
          }}
        />
      );
    }

    // ========== COMMENTED: OTP Page (No longer rendered) ==========
    // if (currentPage === 'otp') {
    //   return (
    //     <OTP
    //       onOTPSuccess={() => {
    //         setCurrentPage('authenticated');
    //       }}
    //       onBack={() => setCurrentPage('login')}
    //     />
    //   );
    // }
  }

  return <>{children}</>;
}