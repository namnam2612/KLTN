# Deployment

## Frontend: Vercel

- Root directory: `UI/frontend`
- Build command: `npm run build`
- Output directory: `dist`
- Environment variables:

```env
VITE_AUTH_API_URL=https://your-auth-service.up.railway.app
VITE_CHAT_API_URL=https://your-chat-service.up.railway.app
```

## Auth API: Railway

- Root directory: `UI/backend`
- Dockerfile: `UI/backend/Dockerfile`
- Public networking: enable
- Health check path: `/health`
- Environment variables:

```env
PORT=3001
CORS_ORIGIN=https://your-frontend.vercel.app

DB_HOST=...
DB_PORT=3306
DB_USER=...
DB_PASSWORD=...
DB_NAME=...

REDIS_URL=...
# Or use REDIS_HOST, REDIS_PORT, REDIS_PASSWORD instead of REDIS_URL.

JWT_SECRET=replace_with_a_strong_random_secret
JWT_ACCESS_TOKEN_EXPIRES_IN=15m
JWT_REFRESH_TOKEN_EXPIRES_IN=7d

BCRYPT_SALT_ROUNDS=10
QUEUE_MAX_CONCURRENT_USERS=5
QUEUE_SESSION_TIMEOUT_SECONDS=1800
QUEUE_TIMEOUT_SECONDS=60
```

Create the MySQL table from `UI/backend/sql/schema.sql` before logging in or registering users.

## Chat/RAG API: Railway

- Root directory: `CHATBOT_FAQ`
- Dockerfile: `CHATBOT_FAQ/Dockerfile`
- Public networking: enable
- Environment variables:

```env
PORT=8000
CORS_ORIGINS=http://localhost:3000,https://your-frontend.vercel.app

LLM_API_KEY=...
LLM_MODEL=...
LLM_BASE_URL=...
USE_WEB_SEARCH=false
```

The Docker image builds chunks and the Chroma index during image build, so the generated `data/chunks` and `data/indexes` folders do not need to be committed.
