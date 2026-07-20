import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { streamJsonLines, API_URL } from '@/lib/api';

function makeFakeResponse({
  ok = true,
  status = 200,
  chunks = [] as string[],
  text = '',
}: {
  ok?: boolean;
  status?: number;
  chunks?: string[];
  text?: string;
}) {
  const encoder = new TextEncoder();
  let index = 0;
  const releaseLock = vi.fn();
  const read = vi.fn(async () => {
    if (index >= chunks.length) {
      return { done: true as const, value: undefined };
    }
    const chunk = chunks[index++];
    return { done: false as const, value: encoder.encode(chunk) };
  });
  const reader = { read, releaseLock };
  const body = { getReader: vi.fn(() => reader) };

  return {
    response: {
      ok,
      status,
      body,
      text: vi.fn().mockResolvedValue(text),
    } as unknown as Response,
    releaseLock,
    read,
  };
}

describe('streamJsonLines', () => {
  let fetchSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchSpy = vi.fn();
    vi.stubGlobal('fetch', fetchSpy);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('prepends API_URL to the given path', async () => {
    const { response, releaseLock } = makeFakeResponse({ chunks: ['data: [DONE]\n'] });
    fetchSpy.mockResolvedValue(response);

    const gen = streamJsonLines('/projects/1/agent/step/script', {});
    await gen.next();

    expect(fetchSpy).toHaveBeenCalledWith(
      `${API_URL}/projects/1/agent/step/script`,
      expect.objectContaining({ method: 'POST' })
    );
    expect(releaseLock).toHaveBeenCalled();
  });

  it('yields parsed JSON objects from valid data: lines', async () => {
    const { response } = makeFakeResponse({
      chunks: ['data: {"type":"progress","value":10}\ndata: {"type":"token","text":"hi"}\n'],
    });
    fetchSpy.mockResolvedValue(response);

    const results: unknown[] = [];
    for await (const chunk of streamJsonLines('/stream', {})) {
      results.push(chunk);
    }

    expect(results).toEqual([
      { type: 'progress', value: 10 },
      { type: 'token', text: 'hi' },
    ]);
  });

  it('stops iterating when a [DONE] line is received', async () => {
    const { response } = makeFakeResponse({
      chunks: ['data: {"type":"progress"}\ndata: [DONE]\n', 'data: {"type":"ignored"}\n'],
    });
    fetchSpy.mockResolvedValue(response);

    const results: unknown[] = [];
    for await (const chunk of streamJsonLines('/stream', {})) {
      results.push(chunk);
    }

    expect(results).toEqual([{ type: 'progress' }]);
  });

  it('skips malformed lines without throwing', async () => {
    const { response } = makeFakeResponse({
      chunks: ['data: not-json\nfoo: bar\ndata: {"type":"ok"}\n'],
    });
    fetchSpy.mockResolvedValue(response);

    const results: unknown[] = [];
    for await (const chunk of streamJsonLines('/stream', {})) {
      results.push(chunk);
    }

    expect(results).toEqual([{ type: 'ok' }]);
  });

  it('throws for non-OK HTTP responses', async () => {
    const { response } = makeFakeResponse({ ok: false, status: 500, text: 'server error' });
    fetchSpy.mockResolvedValue(response);

    await expect(async () => {
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      for await (const _ of streamJsonLines('/stream', {})) {
        // consume
      }
    }).rejects.toThrow('server error');
  });

  it('releases the reader lock after iteration', async () => {
    const { response, releaseLock } = makeFakeResponse({
      chunks: ['data: {"type":"a"}\ndata: [DONE]\n'],
    });
    fetchSpy.mockResolvedValue(response);

    for await (const _ of streamJsonLines('/stream', {})) {
      // consume
    }

    expect(releaseLock).toHaveBeenCalledTimes(1);
  });
});
