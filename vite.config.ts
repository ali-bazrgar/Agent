import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const apiTarget = env.SUPERAGENT_API_URL || 'http://127.0.0.1:8000';

  return {
    plugins: [react()],
    server: {
      host: '0.0.0.0',
      port: 3000,
      proxy: {
        '/api': {
          target: apiTarget,
          changeOrigin: true,
          secure: false,
          // The frontend uses /api/v1/* while FastAPI exposes /v1/*.
          // Keep direct Vite development behavior identical to server.ts.
          rewrite: (path) => path.replace(/^\/api/, ''),
        },
      },
    },
  };
});
