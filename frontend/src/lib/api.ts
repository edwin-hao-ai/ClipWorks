export const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function request(path: string, options: RequestInit = {}) {
  const isFormData = options.body instanceof FormData;
  const headers: Record<string, string> = isFormData
    ? {}
    : { 'Content-Type': 'application/json' };

  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    credentials: 'include',
    headers: {
      ...headers,
      ...(options.headers as Record<string, string> || {}),
    },
  });

  if (!res.ok) {
    const detail = await res.text().catch(() => `${res.status}`);
    throw new Error(`API error ${res.status}: ${detail}`);
  }

  return res.json();
}

async function* streamPost(path: string, body?: unknown) {
  const res = await fetch(`${API_URL}${path}`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => `${res.status}`);
    throw new Error(`API error ${res.status}: ${detail}`);
  }
  if (!res.body) return;
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith('data:')) continue;
        const data = trimmed.slice(5).trim();
        if (data === '[DONE]') return;
        try {
          yield JSON.parse(data);
        } catch {
          yield { type: 'token', text: data };
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

async function* streamGet(path: string) {
  const res = await fetch(`${API_URL}${path}`, {
    method: 'GET',
    credentials: 'include',
    headers: { Accept: 'text/event-stream' },
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => `${res.status}`);
    throw new Error(`API error ${res.status}: ${detail}`);
  }
  if (!res.body) return;
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop() || '';
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith('data:')) continue;
        const data = trimmed.slice(5).trim();
        if (data === '[DONE]') return;
        try {
          yield JSON.parse(data);
        } catch {
          // ignore non-JSON SSE data
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

export async function* streamJsonLines(
  path: string,
  body: unknown
): AsyncGenerator<{ type: string; [key: string]: unknown }> {
  const res = await fetch(`${API_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  const reader = res.body?.getReader();
  if (!reader) throw new Error('No response body');
  const decoder = new TextDecoder();
  let buffer = '';
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed.startsWith('data:')) continue;
        const payload = trimmed.slice(5).trim();
        if (payload === '[DONE]') return;
        try {
          yield JSON.parse(payload);
        } catch {
          // ignore malformed lines
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

export const api = {
  get: (path: string) => request(path),
  post: (path: string, body?: unknown) => request(path, { method: 'POST', body: JSON.stringify(body) }),
  put: (path: string, body?: unknown) => request(path, { method: 'PUT', body: JSON.stringify(body) }),
  delete: (path: string) => request(path, { method: 'DELETE' }),
  postForm: (path: string, formData: FormData) => request(path, { method: 'POST', body: formData }),
  stream: streamPost,
  streamGet,
};
