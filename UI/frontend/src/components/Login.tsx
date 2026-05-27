import { useState } from 'react';
import { motion } from 'motion/react';
import { Mail, Lock, Loader2, AlertCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import Register from './Register';

interface LoginProps {
  onLoginSuccess: () => void;
}

export default function Login({ onLoginSuccess }: LoginProps) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  // const [isAdmin, setIsAdmin] = useState(false); // COMMENTED - No longer used
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const { login } = useAuth();
  const [showRegister, setShowRegister] = useState(false);


  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      if (!email.trim()) {
        setError('Vui lòng nhập email hoặc username');
        setIsLoading(false);
        return;
      }

      if (!password.trim()) {
        setError('Vui lòng nhập mật khẩu');
        setIsLoading(false);
        return;
      }

      if (password.length < 6) {
        setError('Mật khẩu phải có ít nhất 6 ký tự');
        setIsLoading(false);
        return;
      }

      // Call login function - role will be determined from database
      const result = await login(email, password);

      if (result.success) {
        onLoginSuccess();
      } else {
        setError(result.message || 'Lỗi đăng nhập');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-surface text-on-surface font-body overflow-hidden">
      {/* Left Side - Background gradient */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-primary-container via-surface-container to-surface relative overflow-hidden">
        <div className="absolute inset-0">
          <div className="absolute top-10 left-10 w-96 h-96 bg-primary/20 rounded-full blur-3xl"></div>
          <div className="absolute bottom-10 right-10 w-96 h-96 bg-tertiary/20 rounded-full blur-3xl"></div>
        </div>
        <div className="relative z-10 flex flex-col justify-center items-center w-full px-8">
          <motion.div
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6 }}
            className="text-center"
          >
            <h1 className="text-5xl md:text-6xl font-headline font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-primary to-primary-container mb-4">
              AI Chatbot
            </h1>
            <p className="text-lg text-on-surface-variant mb-8">Trợ lý thông minh cho sinh viên Thăng Long</p>
            <div className="bg-surface-container/50 backdrop-blur p-6 rounded-2xl max-w-md mx-auto border border-white/10">
              <p className="text-sm text-on-surface-variant leading-relaxed">
                Hệ thống chatbot hỗ trợ tư vấn, trả lời câu hỏi và cung cấp thông tin cho sinh viên
              </p>
            </div>
          </motion.div>
        </div>
      </div>

      {/* Right Side - Login Form */}
      <div className="w-full lg:w-1/2 flex flex-col justify-center items-center px-8 py-12 bg-surface-container-low">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="w-full max-w-md"
        >
          

          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-xl flex items-start gap-3"
            >
              <AlertCircle className="w-5 h-5 text-red-400 mt-0.5 shrink-0" />
              <p className="text-sm text-red-300">{error}</p>
            </motion.div>
          )}

          {!showRegister ? (
            <form onSubmit={handleSubmit} className="space-y-6">
              <div className="mb-8">
                <h2 className="text-3xl font-headline font-extrabold text-on-surface mb-2">Đăng Nhập</h2>
                <p className="text-on-surface-variant">Sử dụng tài khoản Gmail hoặc email của bạn</p>
              </div>
            {/* Email/Username Input */}
            <div className="space-y-2">
              <label className="text-sm font-headline font-semibold text-on-surface">
                Email hoặc Username
              </label>
              <div className="relative">
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-primary pointer-events-none" />
                <input
                  type="text"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  disabled={isLoading}
                  placeholder="your.email@gmail.com hoặc username"
                  className="w-full pl-12 pr-4 py-3 bg-surface-container border border-white/10 rounded-xl text-on-surface placeholder:text-on-surface-variant/50 outline-none focus:border-primary focus:ring-1 focus:ring-primary/50 transition-all disabled:opacity-50"
                />
              </div>
            </div>

            {/* Password Input */}
            <div className="space-y-2">
              <label className="text-sm font-headline font-semibold text-on-surface">
                Mật Khẩu
              </label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-primary pointer-events-none" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  disabled={isLoading}
                  placeholder="••••••••"
                  className="w-full pl-12 pr-12 py-3 bg-surface-container border border-white/10 rounded-xl text-on-surface placeholder:text-on-surface-variant/50 outline-none focus:border-primary focus:ring-1 focus:ring-primary/50 transition-all disabled:opacity-50"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  disabled={isLoading}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-on-surface-variant hover:text-primary transition-colors disabled:opacity-50"
                >
                  {showPassword ? '👁️' : '👁️‍🗨️'}
                </button>
              </div>
            </div>

            {/* Submit Button */}
            <motion.button
              whileHover={{ scale: isLoading ? 1 : 1.02 }}
              whileTap={{ scale: isLoading ? 1 : 0.98 }}
              disabled={isLoading}
              type="submit"
              className="w-full py-3 bg-gradient-to-r from-primary to-primary-container text-on-primary-container font-headline font-bold rounded-xl shadow-lg shadow-primary/20 hover:shadow-lg hover:shadow-primary/40 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Đang xử lý...
                </>
              ) : (
                'Đăng Nhập'
              )}
            </motion.button>
          </form>
          ) : (
            <div>
              <Register onRegistered={() => { setShowRegister(false); onLoginSuccess(); }} />
            </div>
          )}

          {/* Demo Account Note */}
          <div className="mt-8 p-4 bg-surface-container rounded-xl border border-white/5">
            <p className="text-xs text-on-surface-variant font-semibold mb-2">� Gợi ý:</p>
            <p className="text-xs text-on-surface-variant">Sử dụng username hoặc email đã đăng ký. Bạn chưa có tài khoản? <button onClick={() => setShowRegister(true)} className="text-primary underline">Đăng ký tại đây</button></p>
          </div>
          <div className="mt-4 text-center">
            {!showRegister ? (
              <button onClick={() => setShowRegister(true)} className="text-sm text-primary underline">Đăng Ký</button>
            ) : (
              <button onClick={() => setShowRegister(false)} className="text-sm text-primary underline">Quay lại Đăng Nhập</button>
            )}
          </div>
        </motion.div>
      </div>
    </div>
  );
}