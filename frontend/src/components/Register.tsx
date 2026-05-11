import { useState } from 'react';
import { useAuth } from '../context/AuthContext';

export default function Register({ onRegistered }: { onRegistered?: () => void }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [role, setRole] = useState('user');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { register } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (!username.trim() || !password.trim()) {
      setError('Vui lòng nhập username và mật khẩu');
      return;
    }
    if (password !== confirmPassword) {
      setError('Mật khẩu và xác nhận không khớp');
      return;
    }
    console.log('Register form submit:', { username: username.trim(), password, confirmPassword, role });
    setIsLoading(true);
    const res = await register(username.trim(), password, confirmPassword, role);
    setIsLoading(false);
    if (!res.success) {
      setError(res.message || 'Đăng ký thất bại');
      return;
    }
    if (onRegistered) onRegistered();
  };

  return (
    <div className="w-full max-w-md mx-auto">
      <h2 className="text-2xl font-bold mb-4">Đăng Ký</h2>
      {error && <div className="mb-4 text-sm text-red-400">{error}</div>}
      <form onSubmit={handleSubmit} className="space-y-4">
        <input value={username} onChange={(e) => setUsername(e.target.value)} placeholder="Username" className="w-full p-3 rounded border" />
        <input value={password} onChange={(e) => setPassword(e.target.value)} type="password" placeholder="Password" className="w-full p-3 rounded border" />
        <input value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} type="password" placeholder="Confirm Password" className="w-full p-3 rounded border" />
        <select value={role} onChange={(e) => setRole(e.target.value)} className="w-full p-3 rounded border">
          <option value="user">User</option>
          <option value="admin">Admin</option>
        </select>
        <div className="flex gap-2">
          <button type="submit" disabled={isLoading} className="px-4 py-2 bg-primary text-white rounded">
            {isLoading ? 'Đang xử lý...' : 'Đăng Ký'}
          </button>
        </div>
      </form>
    </div>
  );
}
