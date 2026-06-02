const env = import.meta.env as Record<string, string | undefined>;

function getRequiredClientEnv(name: string): string {
  const value = env[name];

  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }

  return value.replace(/\/+$/, '');
}

export const AUTH_API_URL = getRequiredClientEnv('VITE_AUTH_API_URL');
export const CHAT_API_URL = getRequiredClientEnv('VITE_CHAT_API_URL');
