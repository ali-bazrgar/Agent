import express from 'express';
import path from 'node:path';
import { createServer as createViteServer } from 'vite';
import { createProxyMiddleware } from 'http-proxy-middleware';

const app = express();
const PORT = Number(process.env.PORT ?? 3000);
const FASTAPI_URL = process.env.SUPERAGENT_API_URL ?? 'http://127.0.0.1:8000';

app.disable('x-powered-by');

app.use(
  '/api',
  createProxyMiddleware({
    target: FASTAPI_URL,
    changeOrigin: true,
    pathRewrite: { '^/api': '' },
    proxyTimeout: 65_000,
    timeout: 65_000,
  }),
);

async function startServer(): Promise<void> {
  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath, { index: 'index.html' }));
    app.get('*', (_req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`[SuperAgent] Web server listening on http://0.0.0.0:${PORT}`);
    console.log(`[SuperAgent] API proxy target: ${FASTAPI_URL}`);
  });
}

startServer().catch((error: unknown) => {
  console.error('[SuperAgent] Failed to start server:', error);
  process.exitCode = 1;
});
