# Deployment

This repo is prepared for a mostly-free deployment stack:

- `UI/frontend`: Vercel
- `UI/backend`: Vercel Serverless Functions
- `CHATBOT_FAQ`: Hugging Face Spaces Docker, or Render/VPS if you prefer a normal server
- MySQL: TiDB Cloud Starter
- Redis: Upstash Redis

## 1. MySQL: TiDB Cloud

Create a TiDB Cloud Starter cluster and copy the MySQL-compatible connection values.

Run this SQL once:

```sql
CREATE TABLE IF NOT EXISTS account (
  id INT AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(255) NOT NULL UNIQUE,
  password VARCHAR(255) NOT NULL,
  role VARCHAR(20) NOT NULL DEFAULT 'user',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

The same schema is in `UI/backend/sql/schema.sql`.

## 2. Redis: Upstash

Create an Upstash Redis database and copy the Redis URL.

Use the TLS URL when available, usually shaped like:

```env
REDIS_URL=rediss://...
```

## 3. Auth API: Vercel

Import this GitHub repo as a Vercel project.

- Root directory: `UI/backend`
- Framework preset: Other
- Build command: leave empty, or `npm run lint`
- Output directory: leave empty

Environment variables:

```env
CORS_ORIGIN=https://your-frontend.vercel.app

DB_HOST=...
DB_PORT=4000
DB_USER=...
DB_PASSWORD=...
DB_NAME=...

REDIS_URL=rediss://...

JWT_SECRET=replace_with_a_strong_random_secret
JWT_ACCESS_TOKEN_EXPIRES_IN=15m
JWT_REFRESH_TOKEN_EXPIRES_IN=7d

BCRYPT_SALT_ROUNDS=10
QUEUE_MAX_CONCURRENT_USERS=5
QUEUE_SESSION_TIMEOUT_SECONDS=1800
QUEUE_TIMEOUT_SECONDS=60
```

Health check after deploy:

```text
https://your-auth-backend.vercel.app/health
```

## 4. Chat/RAG API: Hugging Face Spaces

Create a new Hugging Face Space:

- SDK: Docker
- Hardware: CPU Basic
- Visibility: Public or Private

The Space repo must contain the contents of `CHATBOT_FAQ` at its root, including:

```text
Dockerfile
requirements.txt
app/
scripts/
data/
```

Environment variables / secrets:

```env
PORT=8000
CORS_ORIGINS=http://localhost:3000,https://your-frontend.vercel.app

LLM_API_KEY=...
LLM_MODEL=...
LLM_BASE_URL=...
USE_WEB_SEARCH=false
```

The Docker image builds chunks and the Chroma index during image build, so the generated `data/chunks` and `data/indexes` folders do not need to be committed.

## 5. Frontend: Vercel

Import this GitHub repo as a second Vercel project.

- Root directory: `UI/frontend`
- Framework preset: Vite
- Build command: `npm run build`
- Output directory: `dist`

Environment variables:

```env
VITE_AUTH_API_URL=https://your-auth-backend.vercel.app
VITE_CHAT_API_URL=https://your-chat-space.hf.space
```

After frontend deploy, update:

- `UI/backend` Vercel project: `CORS_ORIGIN=https://your-frontend.vercel.app`
- Hugging Face Space: `CORS_ORIGINS=http://localhost:3000,https://your-frontend.vercel.app`
