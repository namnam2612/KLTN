# KLTN - AI Chatbot FAQ

Đây là đồ án xây dựng hệ thống chatbot hỏi đáp FAQ cho sinh viên. Repository gồm hai phần chính:

- `CHATBOT_FAQ`: backend AI/RAG bằng Python FastAPI, xử lý tài liệu, tạo vector index, truy xuất ngữ cảnh và gọi LLM để trả lời.
- `UI`: giao diện React/Vite và backend xác thực Express, quản lý đăng nhập, đăng ký, JWT, phân quyền và hàng đợi người dùng.

## Kiến Trúc

```text
KLTN/
├── CHATBOT_FAQ/        # AI backend: FastAPI + RAG + ChromaDB
├── UI/
│   ├── frontend/       # React + Vite UI
│   └── backend/        # Express auth server + MySQL + Redis
└── README.md
```

Luồng hoạt động chính:

1. Người dùng đăng nhập/đăng ký trên `UI/frontend`.
2. `UI/backend` xác thực tài khoản, phát JWT và kiểm soát số user active qua Redis.
3. Giao diện chat gọi `CHATBOT_FAQ` để tạo/lấy hội thoại và gửi câu hỏi.
4. `CHATBOT_FAQ` truy xuất dữ liệu từ ChromaDB/structured data, gọi LLM và trả câu trả lời kèm nguồn.

## Công Nghệ

### CHATBOT_FAQ

- FastAPI, Uvicorn
- LangChain, ChromaDB
- Sentence Transformers
- PyMuPDF, pdfplumber, pypdf
- SQLite cho lịch sử hội thoại
- LLM API tương thích OpenAI-style chat completions

### UI

- React 19, Vite, TypeScript
- Tailwind CSS
- Express, MySQL, Redis
- JWT, bcrypt

## Yêu Cầu Môi Trường

- Python 3.10+
- Node.js 20+
- npm 10+
- MySQL
- Redis

## Cài Đặt

Clone repository:

```bash
git clone https://github.com/namnam2612/KLTN.git
cd KLTN
```

### 1. Cài CHATBOT_FAQ

```bash
cd CHATBOT_FAQ
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Tạo file `.env` trong `CHATBOT_FAQ`:

```env
APP_NAME=AI FAQ
APP_ENV=dev
APP_HOST=127.0.0.1
APP_PORT=8000

LLM_API_KEY=your_llm_api_key
LLM_MODEL=your_model_name
LLM_BASE_URL=https://your-llm-provider.example.com/v1
```

Nếu cần build lại dữ liệu từ PDF:

```bash
python -m scripts.extract_pdfs
python -m scripts.clean_extracted
python -m scripts.build_chunks
python -m scripts.build_index
```

Chạy AI backend:

```bash
uvicorn app.api.main:app --host 127.0.0.1 --port 8000 --reload
```

API chính:

- `GET /health`
- `POST /ask`
- `GET /api/conversations`
- `POST /api/messages`
- `POST /api/conversations/{conversation_id}/messages`

### 2. Cài UI

```bash
cd ../UI
npm run install-all
```

Tạo file `.env` từ file mẫu:

```bash
cp .env.example .env
```

Cập nhật các biến trong `.env`:

```env
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=your_db_name

JWT_SECRET=replace_with_a_strong_random_secret
JWT_ACCESS_TOKEN_EXPIRES_IN=15m
JWT_REFRESH_TOKEN_EXPIRES_IN=7d

REDIS_HOST=127.0.0.1
REDIS_PORT=6379

PORT=3001
CORS_ORIGIN=http://localhost:3000

VITE_AUTH_API_URL=http://localhost:3001
VITE_CHAT_API_URL=http://localhost:8000
```

Chạy MySQL và Redis trước khi khởi động UI backend.

Chạy cả frontend và auth backend:

```bash
npm start
```

Hoặc chạy riêng:

```bash
npm run backend
npm run frontend
```

Mặc định:

- Frontend: `http://localhost:3000`
- Auth backend: `http://localhost:3001`
- AI backend: `http://localhost:8000`

## Database Auth

`UI/backend` dùng bảng `account` trong MySQL. Bảng cần có tối thiểu các cột:

```sql
CREATE TABLE account (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(255) NOT NULL UNIQUE,
  password VARCHAR(255) NOT NULL,
  role VARCHAR(50) NOT NULL DEFAULT 'user'
);
```

Mật khẩu account mới được hash bằng bcrypt. Đăng ký từ UI luôn tạo role `user`.

## Kiểm Tra

Backend/UI TypeScript:

```bash
cd UI
npm run lint
npm run build
```

Test queue backend:

```bash
cd UI/backend
npm run test:concurrent
npm run test:load
```

Test truy xuất RAG thủ công:

```bash
cd CHATBOT_FAQ
python -m scripts.test_search
python -m scripts.test_structured_lookup
```

## Lưu Ý Bảo Mật

- Không commit `.env`.
- Không commit API key, JWT secret, DB password.
- `UI/.env.example` chỉ là file mẫu và có thể commit.
- Các file sinh ra khi chạy như `node_modules`, `dist`, `venv`, `__pycache__`, `data/indexes` không nên commit.

## Gợi Ý Quy Trình Git

Nên tạo/cập nhật README ở local rồi commit và push:

```bash
git add README.md
git commit -m "Add project README"
git push origin master
```

Cách này tốt hơn sửa trực tiếp trên GitHub vì local repo luôn đồng bộ lịch sử thay đổi, dễ kiểm tra build/lint trước khi push và tránh conflict.
