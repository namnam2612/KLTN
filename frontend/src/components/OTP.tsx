import { useState, useEffect } from 'react';
import { motion } from 'motion/react';
import { Loader2, AlertCircle, CheckCircle, Clock } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface OTPProps {
  onOTPSuccess: () => void;
  onBack: () => void;
}

export default function OTP({ onOTPSuccess, onBack }: OTPProps) {
  const [otp, setOtp] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [timeLeft, setTimeLeft] = useState(60);
  const [isExpired, setIsExpired] = useState(false);
  const { verifyOTP } = useAuth();

  // Countdown timer
  useEffect(() => {
    if (timeLeft <= 0) {
      setIsExpired(true);
      return;
    }

    const timer = setInterval(() => {
      setTimeLeft(prev => prev - 1);
    }, 1000);

    return () => clearInterval(timer);
  }, [timeLeft]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!otp.trim()) {
      setError('Vui lòng nhập mã OTP');
      return;
    }

    if (otp.length !== 6) {
      setError('Mã OTP phải có 6 chữ số');
      return;
    }

    if (isExpired) {
      setError('Mã OTP đã hết hạn. Vui lòng quay lại đăng nhập để nhận mã mới.');
      return;
    }

    setIsLoading(true);

    try {
      const result = await verifyOTP(otp);

      if (result.success) {
        onOTPSuccess();
      } else {
        setError(result.message || 'Mã OTP không chính xác');
        setOtp('');
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleResend = async () => {
    // Reset timer and OTP
    setTimeLeft(60);
    setIsExpired(false);
    setOtp('');
    setError('');
    // TODO: Call resend OTP API
    setError('OTP đã được gửi lại');
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
              Xác Minh Danh Tính
            </h1>
            <p className="text-lg text-on-surface-variant mb-8">Nhập mã OTP để tiếp tục</p>
            <div className="bg-surface-container/50 backdrop-blur p-6 rounded-2xl max-w-md mx-auto border border-white/10">
              <p className="text-sm text-on-surface-variant leading-relaxed">
                Một mã OTP 6 chữ số đã được gửi đến email của bạn. Mã này sẽ hết hạn sau 60 giây.
              </p>
            </div>
          </motion.div>
        </div>
      </div>

      {/* Right Side - OTP Form */}
      <div className="w-full lg:w-1/2 flex flex-col justify-center items-center px-8 py-12 bg-surface-container-low">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="w-full max-w-md"
        >
          <div className="mb-8">
            <h2 className="text-3xl font-headline font-extrabold text-on-surface mb-2">Nhập Mã OTP</h2>
            <p className="text-on-surface-variant">Kiểm tra email để lấy mã 6 chữ số</p>
          </div>

          {/* Timer Status */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className={`mb-6 p-4 rounded-xl flex items-center gap-3 border ${
              isExpired
                ? 'bg-red-500/10 border-red-500/30'
                : timeLeft <= 10
                ? 'bg-yellow-500/10 border-yellow-500/30'
                : 'bg-primary/10 border-primary/30'
            }`}
          >
            <Clock className={`w-5 h-5 ${isExpired ? 'text-red-400' : timeLeft <= 10 ? 'text-yellow-400' : 'text-primary'}`} />
            <div className="flex-1">
              <p className={`text-sm font-headline font-semibold ${isExpired ? 'text-red-300' : 'text-on-surface'}`}>
                {isExpired ? 'Mã đã hết hạn' : `Hết hạn sau ${timeLeft}s`}
              </p>
            </div>
          </motion.div>

          {error && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className={`mb-6 p-4 rounded-xl flex items-start gap-3 border ${
                error.includes('gửi lại')
                  ? 'bg-primary/10 border-primary/30'
                  : 'bg-red-500/10 border-red-500/30'
              }`}
            >
              {error.includes('gửi lại') ? (
                <CheckCircle className="w-5 h-5 text-primary mt-0.5 shrink-0" />
              ) : (
                <AlertCircle className="w-5 h-5 text-red-400 mt-0.5 shrink-0" />
              )}
              <p className={`text-sm ${error.includes('gửi lại') ? 'text-primary' : 'text-red-300'}`}>
                {error}
              </p>
            </motion.div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* OTP Input */}
            <div className="space-y-2">
              <label className="text-sm font-headline font-semibold text-on-surface">
                Mã OTP (6 chữ số)
              </label>
              <input
                type="text"
                value={otp}
                onChange={(e) => {
                  const value = e.target.value.replace(/\D/g, '').slice(0, 6);
                  setOtp(value);
                }}
                disabled={isLoading || isExpired}
                placeholder="000000"
                maxLength={6}
                className="w-full px-4 py-4 bg-surface-container border-2 border-white/10 rounded-xl text-on-surface placeholder:text-on-surface-variant/50 outline-none focus:border-primary focus:ring-2 focus:ring-primary/50 transition-all disabled:opacity-50 text-center text-2xl tracking-widest font-mono font-bold"
              />
              <p className="text-xs text-on-surface-variant text-right">
                {otp.length}/6
              </p>
            </div>

            {/* Submit Button */}
            <motion.button
              whileHover={{ scale: isLoading || isExpired ? 1 : 1.02 }}
              whileTap={{ scale: isLoading || isExpired ? 1 : 0.98 }}
              disabled={isLoading || isExpired}
              type="submit"
              className="w-full py-3 bg-gradient-to-r from-primary to-primary-container text-on-primary-container font-headline font-bold rounded-xl shadow-lg shadow-primary/20 hover:shadow-lg hover:shadow-primary/40 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {isLoading ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  Đang xác minh...
                </>
              ) : isExpired ? (
                'Mã đã hết hạn'
              ) : (
                'Xác Minh OTP'
              )}
            </motion.button>
          </form>

          {/* Resend and Back Options */}
          <div className="mt-8 space-y-4">
            <button
              onClick={handleResend}
              disabled={isLoading || !isExpired}
              className="w-full py-2 px-4 bg-surface-container border border-white/10 text-primary rounded-xl hover:bg-surface-container-high transition-all disabled:opacity-50 disabled:cursor-not-allowed font-headline font-semibold text-sm"
            >
              Gửi lại mã OTP
            </button>

            <button
              onClick={onBack}
              disabled={isLoading}
              className="w-full py-2 px-4 bg-surface-container border border-white/10 text-on-surface-variant rounded-xl hover:bg-surface-container-high hover:text-on-surface transition-all disabled:opacity-50 font-headline font-semibold text-sm"
            >
              Quay Lại Đăng Nhập
            </button>
          </div>
        </motion.div>
      </div>
    </div>
  );
}