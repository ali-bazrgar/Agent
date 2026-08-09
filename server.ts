import express from 'express';
import path from 'node:path';
import { randomUUID } from 'node:crypto';
import { spawn, type ChildProcess } from 'node:child_process';
import { createServer as createViteServer } from 'vite';
import { createProxyMiddleware } from 'http-proxy-middleware';

const app = express();
const PORT = Number(process.env.PORT ?? 3000);
const FASTAPI_URL = process.env.SUPERAGENT_API_URL ?? 'http://127.0.0.1:8000';
const AUTO_START_API = process.env.NODE_ENV !== 'production' && process.env.SUPERAGENT_AUTO_START_API !== '0';
const API_PROXY_TIMEOUT_MS = Number(process.env.SUPERAGENT_API_PROXY_TIMEOUT_MS ?? 10 * 60 * 1000);
const API_STARTUP_TIMEOUT_MS = Number(process.env.SUPERAGENT_API_STARTUP_TIMEOUT_MS ?? 15_000);
const API_STARTUP_POLL_MS = Number(process.env.SUPERAGENT_API_STARTUP_POLL_MS ?? 250);
let apiProcess: ChildProcess | null = null;

app.disable('x-powered-by');

function apiHealthUrl(): string {
  const base = FASTAPI_URL.replace(/\/$/, '');
  return `${base}/health`;
}

async function isApiReachable(): Promise<boolean> {
  try {
    const response = await fetch(apiHealthUrl(), { signal: AbortSignal.timeout(1500) });
    return response.ok || response.status < 500;
  } catch {
    return false;
  }
}

function pythonCandidates(): string[] {
  return process.platform === 'win32'
    ? [path.join(process.cwd(), '.venv', 'Scripts', 'python.exe'), 'python']
    : [path.join(process.cwd(), '.venv', 'bin', 'python'), 'python3', 'python'];
}

async function waitForApi(timeoutMs: number): Promise<boolean> {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (await isApiReachable()) return true;
    await new Promise((resolve) => setTimeout(resolve, API_STARTUP_POLL_MS));
  }
  return false;
}

async function ensureApi(): Promise<void> {
  if (!AUTO_START_API || await isApiReachable()) return;

  console.log('[SuperAgent] FastAPI is not reachable; attempting to start the local API automatically.');
  let lastError: unknown = null;
  for (const python of pythonCandidates()) {
    try {
      const port = new URL(FASTAPI_URL).port || '8000';
      const child = spawn(python, ['-m', 'uvicorn', 'superagent.api.app:app', '--host', '127.0.0.1', '--port', port], {
        cwd: process.cwd(), stdio: ['ignore', 'pipe', 'pipe'], env: { ...process.env, PYTHONUNBUFFERED: '1' }, windowsHide: true,
      });
      child.stdout?.on('data', (chunk: Buffer) => process.stdout.write(`[SuperAgent API] ${chunk}`));
      child.stderr?.on('data', (chunk: Buffer) => process.stderr.write(`[SuperAgent API] ${chunk}`));
      child.on('exit', (code, signal) => {
        if (apiProcess === child) apiProcess = null;
        console.log(`[SuperAgent] Managed API process exited (code=${code ?? 'null'}, signal=${signal ?? 'none'})`);
      });
      apiProcess = child;
      if (await waitForApi(API_STARTUP_TIMEOUT_MS)) {
        console.log('[SuperAgent] Local FastAPI is ready.');
        return;
      }
      child.kill();
      apiProcess = null;
      lastError = new Error(`FastAPI did not become healthy within ${API_STARTUP_TIMEOUT_MS}ms`);
    } catch (error) {
      lastError = error;
    }
  }
  console.warn(`[SuperAgent] Could not auto-start FastAPI${lastError ? `: ${String(lastError)}` : ''}. Start it with: uvicorn superagent.api.app:app --host 127.0.0.1 --port 8000`);
}

app.use('/api', createProxyMiddleware({
  target: FASTAPI_URL,
  changeOrigin: true,
  pathRewrite: { '^/api': '' },
  proxyTimeout: API_PROXY_TIMEOUT_MS,
  timeout: API_PROXY_TIMEOUT_MS,
  on: {
    proxyReq: (proxyReq, req) => {
      const incoming = req.headers['x-request-id'];
      const requestId = typeof incoming === 'string' && incoming ? incoming : randomUUID();
      req.headers['x-request-id'] = requestId;
      proxyReq.setHeader('x-request-id', requestId);
      console.log(`[SuperAgent Proxy] ${req.method} ${req.originalUrl} -> ${FASTAPI_URL}${req.url} request_id=${requestId}`);
    },
    proxyRes: (proxyRes, req) => {
      const requestId = proxyRes.headers['x-request-id'] ?? req.headers['x-request-id'] ?? 'unknown';
      console.log(`[SuperAgent Proxy] response ${proxyRes.statusCode} ${req.method} ${req.originalUrl} request_id=${requestId}`);
    },
    error: (error, req, res) => {
      const requestId = req.headers['x-request-id'] ?? 'unknown';
      console.error(`[SuperAgent Proxy] error ${req.method} ${req.originalUrl} request_id=${requestId}:`, error);
      if (res.headersSent) return;
      res.statusCode = 503;
      res.setHeader('Content-Type', 'application/json; charset=utf-8');
      res.setHeader('x-request-id', String(requestId));
      res.end(JSON.stringify({
        error: 'api_unavailable',
        request_id: requestId,
        message: `FastAPI backend is unavailable at ${FASTAPI_URL}. ${error instanceof Error ? error.message : String(error)}`,
        path: req.url,
      }));
    },
  },
}));

async function startServer(): Promise<void> {
  await ensureApi();

  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({ server: { middlewareMode: true }, appType: 'spa' });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath, { index: 'index.html' }));
    app.get('*', (_req, res) => res.sendFile(path.join(distPath, 'index.html')));
  }

  const server = app.listen(PORT, '0.0.0.0', () => {
    console.log(`[SuperAgent] Web server listening on http://0.0.0.0:${PORT}`);
    console.log(`[SuperAgent] API proxy target: ${FASTAPI_URL}`);
    console.log(`[SuperAgent] API proxy timeout: ${API_PROXY_TIMEOUT_MS}ms`);
  });

  const shutdown = () => {
    if (apiProcess && !apiProcess.killed) apiProcess.kill();
    server.close();
  };
  process.once('SIGINT', shutdown);
  process.once('SIGTERM', shutdown);
}

startServer().catch((error: unknown) => {
  console.error('[SuperAgent] Failed to start server:', error);
  process.exitCode = 1;
});
