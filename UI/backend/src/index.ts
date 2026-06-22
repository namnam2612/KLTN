import app, { CORS_ORIGIN } from './app';
import { getNumberEnv } from './config/env';

const PORT = getNumberEnv('PORT', 3001);

app.listen(PORT, () => {
  console.log(`🚀 Auth server running on port ${PORT}`);
  console.log(`⏳ Queue service enabled`);
  console.log(`🌐 CORS enabled for ${CORS_ORIGIN}`);
});
