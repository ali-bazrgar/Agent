export type DiagnosticEvent = {
  type: string;
  fields?: Record<string, unknown>;
};

const SESSION_KEY = 'superagent.diagnostics.session';
const SESSION_STARTED_KEY = 'superagent.diagnostics.started';
let installed = false;
let originalFetch: typeof window.fetch | null = null;
let enabled = true;

function targetInfo(target: EventTarget | null): Record<string, unknown> {
  if (!(target instanceof HTMLElement)) return {};
  return {
    tag: target.tagName.toLowerCase(),
    id: target.id || undefined,
    role: target.getAttribute('role') || undefined,
    test_id: target.getAttribute('data-testid') || undefined,
    aria_label: target.getAttribute('aria-label') || undefined,
    text: target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement
      ? undefined
      : (target.innerText || target.textContent || '').trim().slice(0, 160) || undefined,
    href: target instanceof HTMLAnchorElement ? target.getAttribute('href') : undefined,
  };
}

function requestMetadata(body: BodyInit | null | undefined): Record<string, unknown> {
  if (!body) return {};
  if (typeof body !== 'string') return { body_type: typeof body };
  try {
    const parsed = JSON.parse(body) as Record<string, unknown>;
    const metadata: Record<string, unknown> = { body_keys: Object.keys(parsed), body_bytes: body.length };
    if (Array.isArray(parsed.attachments)) metadata.attachment_count = parsed.attachments.length;
    if (typeof parsed.message === 'string') metadata.message_length = parsed.message.length;
    if (Array.isArray(parsed.conversation_history)) metadata.history_count = parsed.conversation_history.length;
    return metadata;
  } catch {
    return { body_bytes: body.length, body_format: 'non-json' };
  }
}

function emit(event: DiagnosticEvent): void {
  if (!enabled) return;
  const payload = JSON.stringify({ type: event.type, fields: event.fields ?? {} });
  const url = '/api/v1/diagnostics/events';
  if (navigator.sendBeacon) {
    try {
      navigator.sendBeacon(url, new Blob([payload], { type: 'application/json' }));
      return;
    } catch {
      // Fall through to fetch.
    }
  }
  if (originalFetch) void originalFetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: payload }).catch(() => undefined);
}

export function installDiagnostics(): () => void {
  if (installed) return () => undefined;
  installed = true;
  originalFetch = window.fetch.bind(window);

  const onClick = (event: MouseEvent) => {
    emit({ type: 'ui.click', fields: { ...targetInfo(event.target), x: event.clientX, y: event.clientY, path: window.location.pathname } });
  };
  const onError = (event: ErrorEvent) => emit({ type: 'error', fields: { source: 'window', message: event.message, filename: event.filename, line: event.lineno, column: event.colno, stack: event.error?.stack } });
  const onRejection = (event: PromiseRejectionEvent) => emit({ type: 'error', fields: { source: 'unhandledrejection', reason: String(event.reason), stack: event.reason?.stack } });
  const onVisibility = () => emit({ type: 'ui.visibility', fields: { state: document.visibilityState } });

  document.addEventListener('click', onClick, true);
  window.addEventListener('error', onError);
  window.addEventListener('unhandledrejection', onRejection);
  document.addEventListener('visibilitychange', onVisibility);

  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = typeof input === 'string' ? input : input instanceof URL ? input.toString() : input.url;
    const method = init?.method || (input instanceof Request ? input.method : 'GET');
    const started = performance.now();
    try {
      const response = await originalFetch!(input, init);
      emit({ type: 'api.response', fields: { method, url, status: response.status, ok: response.ok, duration_ms: Math.round((performance.now() - started) * 1000) / 1000, request: requestMetadata(init?.body) } });
      return response;
    } catch (error) {
      emit({ type: 'api.error', fields: { method, url, duration_ms: Math.round((performance.now() - started) * 1000) / 1000, error: String(error), request: requestMetadata(init?.body) } });
      throw error;
    }
  };

  if (!sessionStorage.getItem(SESSION_STARTED_KEY)) {
    sessionStorage.setItem(SESSION_STARTED_KEY, '1');
    emit({ type: 'session.start', fields: { path: window.location.pathname, user_agent: navigator.userAgent, viewport: { width: window.innerWidth, height: window.innerHeight } } });
  }
  return () => {
    document.removeEventListener('click', onClick, true);
    window.removeEventListener('error', onError);
    window.removeEventListener('unhandledrejection', onRejection);
    document.removeEventListener('visibilitychange', onVisibility);
    if (originalFetch) window.fetch = originalFetch;
    originalFetch = null;
    installed = false;
  };
}

export function setDiagnosticsEnabled(value: boolean): void {
  enabled = value;
  localStorage.setItem(SESSION_KEY, value ? 'on' : 'off');
}

export function isDiagnosticsEnabled(): boolean {
  return localStorage.getItem(SESSION_KEY) !== 'off';
}

export function exportDiagnostics(): void {
  window.open('/api/v1/diagnostics/export', '_blank', 'noopener,noreferrer');
}
