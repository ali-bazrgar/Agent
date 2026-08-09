import express from 'express';
import path from 'node:path';
import { spawn, type ChildProcess } from 'node:child_process';
import { createServer as createViteServer } from 'vite';
import { createProxyMiddleware } from 'http-proxy-middleware';

const app = express();
const PORT = Number(process.env.PORT ?? 3000);
const FASTAPI_URL = process.env.SUPERAGENT_API_URL ?? 'http://127.0.0.1:8000';
const AUTO_START_API = process.env.NODE_ENV !== 'production' && process.env.SUPERAGENT_AUTO_START_API !== '0';
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
  const candidates = process.platform === 'win32'
    ? [path.join(process.cwd(), '.venv', 'Scripts', 'python.exe'), 'python']
    : [path.join(process.cwd(), '.venv', 'bin', 'python'), 'python3', 'python'];
  return candidates;
}

function spawnApi(): ChildProcess {
  const python = pythonCandidates()[0];
  const args = ['-m', 'uvicorn', 'superagent.api.app:app', '--host', '127.0.0.1', '--port', new URL(FASTAPI_URL).port || '8000'];
  const child = spawn(python, args, {
    cwd: process.cwd(),
    stdio: ['ignore', 'pipe', 'pipe'],
    env: { ...process.env, PYTHONUNBUFFERED: '1' },
    windowsHide: true,
  });
  child.stdout?.on('data', (chunk: Buffer) => process.stdout.write(`[SuperAgent API] ${chunk}`));
  child.stderr?.on('data', (chunk: Buffer) => process.stderr.write(`[SuperAgent API] ${chunk}`));
  child.on('exit', (code, signal) => {
    if (apiProcess === child) apiProcess = null;
    console.log(`[SuperAgent] Managed API process exited (code=${code ?? 'null'}, signal=${signal ?? 'none'})`);
  });
  return child;
}

async function ensureApi(): Promise<void> {
  if (!AUTO_START_API || await isApiReachable()) return;

  console.log('[SuperAgent] FastAPI is not reachable; attempting to start the local API automatically.');
  const candidates = pythonCandidates();
  let lastError: unknown = null;
  for (const candidate of candidates) {
    try {
      const python = candidate;
      const args = ['-m', 'uvicorn', 'superagent.api.app:app', '--host', '127.0.0.1', '--port', new URL(FASTAPI_URL).port || '8000'];
      const child = spawn(python, args, { cwd: process.cwd(), stdio: ['ignore', 'pipe', 'pipe'], env: { ...process.env, PYTHONUNBUFFERED: '1' }, windowsHide: true });
      child.stdout?.on('data', (chunk: Buffer) => process.stdout.write(`[SuperAgent API] ${chunk}`));
      child.stderr?.on('data', (chunk: Buffer) => process.stderr.write(`[SuperAgent API] ${chunk}`));
      apiProcess = child;
      await new Promise<void>((resolve) => setTimeout(resolve, 900));
      if (await isApiReachable()) {
        console.log('[SuperAgent] Local FastAPI is ready.');
        return;
      }
      child.kill();
      apiProcess = null;
    } catch (error) {
      lastError = error;
    }
  }
  console.warn(`[SuperAgent] Could not auto-start FastAPI${lastError ? `: ${String(lastError)}` : ''}. Start it with: uvicorn superagent.api.app:app --host 127.0.0.1 --port 8000`);
}

app.use(
  '/api',
  createProxyMiddleware({
    target: FASTAPI_URL,
    changeOrigin: true,
    pathRewrite: { '^/api': '' },
    proxyTimeout: 65_000,
    timeout: 65_000,
    onError: (_error, req, res) => {
      if (!res.headersSent) {
        res.statusCode = 503;
        res.setHeader('Content-Type', 'application/json; charset=utf-8');
        res.end(JSON.stringify({
          error: 'api_unavailable',
          message: `FastAPI backend is unavailable at ${FASTAPI_URL}. Start the Python API or restart the web server with auto-start enabled.`,
          path: req.url,
        }));
      }
    },
  }),
);

async function startServer(): Promise<void> {
  await ensureApi();

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

  const server = app.listen(PORT, '0.0.0.0', () => {
    console.log(`[SuperAgent] Web server listening on http://0.0.0.0:${PORT}`);
    console.log(`[SuperAgent] API proxy target: ${FASTAPI_URL}`);
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
