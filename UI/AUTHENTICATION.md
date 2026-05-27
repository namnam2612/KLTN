# 🤖 AI Chatbot - Student Q&A Assistant

Hệ thống chatbot hỗ trợ tư vấn, trả lời câu hỏi cho sinh viên với các tính năng authentication đơn giản và admin authorization.

## ✨ Tính Năng

### 1. **Xác Thực Email & Đăng Nhập**
- ✅ Email bất kỳ (Gmail hoặc email khác)
- ✅ Mật khẩu bảo mật (tối thiểu 6 ký tự)
- ✅ Giao diện login tương ứng với theme chatbot
- ✅ **Không cần OTP** - Login trực tiếp đến chatbot

### 2. **OTP Verification (Commented)**
- ⏸️ OTP flow đã được comment lại
- ⏸️ Không phát sinh OTP trong quá trình login
- ⏸️ Tất cả users (trừ admin) được assign role `user`

### 3. **Admin Account**
- ✅ Tài khoản admin: `email: admin@gmail.com`, `password: admin`
- ✅ Admin vào thẳng trang chatbot (không cần OTP)
- ✅ Nó là account đặc biệt để test admin features

### 4. **User Roles & Authorization**
- ✅ **Admin**: Có thể thấy nút "Admin Panel" trong sidebar
- ✅ **User**: Nút admin bị ẩn (mặc định role cho non-admin users)
- ✅ AuthGuard bảo vệ trang chatbot (phải đăng nhập)
- ✅ Logout button trong sidebar

### 5. **Giao Diện (UI/UX)**
- ✅ Material Design 3 theme (dark mode)
- ✅ Login page tương ứng với background chatbot
- ✅ OTP page tương ứng theme
- ✅ Animations mượt mà với Framer Motion
- ✅ Responsive design

## 🚀 Hướng Dẫn Chạy

### Yêu Cầu
- **Node.js** v20+
- **npm** v10+
- **Redis** (chạy ở `localhost:6379`)

### 1. Chuẩn Bị Redis
Đảm bảo Redis đã được chạy:
```bash
redis-cli ping
# Output: PONG
```

### 2. Cài Dependencies
```bash
npm install
```

### 3. Chạy Backend Server (Terminal 1)
```bash
npm run server
```
Backend sẽ chạy ở `http://localhost:3001`

```
🚀 Auth server running on port 3001
📧 OTP expires after 60 seconds
🔐 Admin account: email=admin@gmail.com, password=admin (no OTP required)
```

### 4. Chạy Frontend (Terminal 2)
```bash
npm run dev
```
Frontend sẽ chạy ở `http://localhost:3000`

## 📋 Cấu Trúc Project

```
├── src/
│   ├── components/
│   │   ├── Login.tsx           # Form đăng nhập
│   │   ├── OTP.tsx             # COMMENTED - OTP flow disabled
│   │   └── AuthGuard.tsx        # Component bảo vệ routes
│   ├── context/
│   │   └── AuthContext.tsx      # Auth state management
│   ├── hooks/
│   │   └── useRequestQueue.ts   # Queue management
│   ├── App.tsx                  # Main chatbot interface
│   ├── Admin.tsx                # Admin panel
│   └── main.tsx                 # Entry point
├── server/
│   └── auth.ts                  # Backend API (Express + Redis)
├── package.json
├── .env                         # Environment variables
└── README.md
```

## 🔐 API Endpoints

### 1. **POST /api/auth/login**
Đăng nhập user (không cần OTP verification)

**Request:**
```json
{
  "email": "student@gmail.com",
  "password": "securePassword123",
  "sessionId": "session-xxx"
}
```

**Response (Success):**
```json
{
  "success": true,
  "message": "Login successful",
  "canEnter": true,
  "role": "user",
  "token": "token-student@gmail.com-1234567890",
  "email": "student@gmail.com",
  "sessionId": "session-xxx"
}
```

**Response (Error):**
```json
{
  "success": false,
  "message": "Email và mật khẩu là bắt buộc"
}
```

### 2. **POST /api/auth/verify-otp** (COMMENTED)
⏸️ **Endpoint này đã bị disable** - OTP verification không còn được sử dụng

### 3. **POST /api/auth/resend-otp** (COMMENTED)
⏸️ **Endpoint này đã bị disable** - Không phát sinh OTP

### 4. **POST /api/auth/logout**
Đăng xuất

## 🧪 Kiểm Tra Nhanh

### Tài Khoản Admin
- **Email:** `admin@gmail.com`
- **Password:** `admin`
- **Kết quả:** Vào thẳng trang chatbot (role: `admin`)

### Tài Khoản User (Regular User)
- **Email:** `user@gmail.com`
- **Password:** `password123`
- **Kết quả:** Vào thẳng trang chatbot (role: `user`, không có Admin Panel)

## 🎨 Theme & Styling

- **Color Theme:** Material Design 3
- **Font:** Manrope (headline), Inter (body)
- **CSS Framework:** Tailwind CSS v4
- **Animations:** Framer Motion

## 📱 Responsive Design

- ✅ Desktop
- ✅ Tablet
- ✅ Mobile

## 🔄 Authentication Flow

```
1. User enters email & password
   ↓
2. Validate email format (has @) & password length (min 6 chars)
   ↓
3. Backend checks if admin account
   ├─ YES → Return role: "admin"
   └─ NO → Return role: "user"
   ↓
4. ⏸️ COMMENTED: OTP verification step (no longer used)
   
5. Frontend stores user info & token
   ↓
6. AuthGuard directs to chatbot
   ├─ Authenticated → Show Chatbot
   └─ Not Auth → Redirect to Login
```

## 🐛 Troubleshooting

### Redis Connection Error
```
Error: Redis did not connect properly
```
**Solution:** Đảm bảo Redis đang chạy
```bash
redis-cli
```

### OTP Not Received (COMMENTED)
⏸️ **OTP flow đã bị disable** - Không phát sinh OTP nữa

### CORS Error
```
Error: Access to XMLHttpRequest blocked by CORS policy
```
**Solution:** Backend đã enable CORS ở port 3001

## 📝 Ghi Chú

- **OTP expiration:** COMMENTED - OTP flow đã bị disable
- **Admin account:** `admin@gmail.com` với role `admin`
- **User account:** Bất kỳ email nào có định dạng hợp lệ với role `user`
- **Default behavior:** Tất cả users (trừ admin) được assign role `user`
- **Token storage:** LocalStorage (nên sử dụng HttpOnly Cookies ở production)

## 🚀 Production Deployment

1. **Implement Real Password Validation**: Thay thế simple password check bằng bcrypt/argon2
2. **Use JWT**: Implement JWT tokens thay vì string tokens
3. **Database**: Lưu user info vào database (MongoDB/PostgreSQL) thay vì Redis-only
4. **HTTPS**: Deploy trên HTTPS
5. **Session Management**: Implement proper session management thay vì sessionId string
5. **Security**: Implement rate limiting, CSRF protection

## 📞 Support

Nếu có vấn đề, kiểm tra:
- Redis đang chạy
- Port 3000 (frontend) và 3001 (backend) không bị chiếm
- Node.js version >= 20
- npm dependencies installed

---

**Tạo bởi:** Chatbot Development Team  
**Version:** 1.0.0  
**Last Updated:** 2024
