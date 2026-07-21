import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeAll, beforeEach } from 'vitest';
import { AgentChat } from '@/components/project/AgentChat';
import { api } from '@/lib/api';

beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

vi.mock('@/lib/api', () => ({
  api: {
    post: vi.fn(),
    stream: vi.fn(),
  },
}));

beforeEach(() => {
  vi.clearAllMocks();
});

function makeAsyncIterator<T>(items: T[], signal?: AbortSignal): AsyncIterableIterator<T> {
  let idx = 0;
  return {
    [Symbol.asyncIterator]() {
      return this;
    },
    async next() {
      if (signal?.aborted) {
        throw new DOMException('The operation was aborted', 'AbortError');
      }
      if (idx < items.length) {
        return { value: items[idx++], done: false };
      }
      return { value: undefined, done: true };
    },
  };
}

function makeHangingIterator(signal?: AbortSignal): AsyncIterableIterator<unknown> {
  let pendingReject: ((reason?: unknown) => void) | null = null;
  signal?.addEventListener('abort', () => {
    pendingReject?.(new DOMException('The operation was aborted', 'AbortError'));
  });
  return {
    [Symbol.asyncIterator]() {
      return this;
    },
    async next() {
      if (signal?.aborted) {
        throw new DOMException('The operation was aborted', 'AbortError');
      }
      // Never resolve naturally; rely on cancellation to reject the pending read.
      return new Promise((_resolve, reject) => {
        pendingReject = reject;
      });
    },
  };
}

describe('AgentChat vibe mode', () => {
  it('renders question message', () => {
    render(
      <AgentChat
        projectId="p1"
        mode="vibe"
        onStatusChange={() => {}}
        initialMessages={[{ role: 'agent', text: 'What format?' }]}
      />
    );
    expect(screen.getByText('What format?')).toBeInTheDocument();
  });

  it('sends message to vibe stream endpoint on submit', async () => {
    (api.stream as ReturnType<typeof vi.fn>).mockImplementation((_path, _body, signal) =>
      makeAsyncIterator([{ type: 'done' }], signal)
    );

    render(<AgentChat projectId="p1" mode="vibe" onStatusChange={() => {}} />);

    const input = screen.getByPlaceholderText('描述你的 Vibe 视频想法…');
    fireEvent.change(input, { target: { value: 'make a promo' } });
    fireEvent.submit(input.closest('form')!);

    await waitFor(() => {
      expect(api.stream).toHaveBeenCalledWith(
        '/projects/p1/agent/vibe/stream',
        {
          message: 'make a promo',
        },
        expect.any(AbortSignal)
      );
    });
  });

  it('appends token events to streaming text', async () => {
    (api.stream as ReturnType<typeof vi.fn>).mockImplementation((_path, _body, signal) =>
      makeAsyncIterator(
        [
          { type: 'token', text: 'Hello' },
          { type: 'token', text: ' world' },
          { type: 'done' },
        ],
        signal
      )
    );

    render(<AgentChat projectId="p1" mode="vibe" onStatusChange={() => {}} />);

    const input = screen.getByPlaceholderText('描述你的 Vibe 视频想法…');
    fireEvent.change(input, { target: { value: 'test' } });
    fireEvent.submit(input.closest('form')!);

    await waitFor(() => {
      expect(screen.getByText('Hello world')).toBeInTheDocument();
    });
  });

  it('adds question events as agent messages', async () => {
    (api.stream as ReturnType<typeof vi.fn>).mockImplementation((_path, _body, signal) =>
      makeAsyncIterator([{ type: 'question', text: 'Which format?' }, { type: 'done' }], signal)
    );

    render(<AgentChat projectId="p1" mode="vibe" onStatusChange={() => {}} />);

    const input = screen.getByPlaceholderText('描述你的 Vibe 视频想法…');
    fireEvent.change(input, { target: { value: 'test' } });
    fireEvent.submit(input.closest('form')!);

    await waitFor(() => {
      expect(screen.getByText('Which format?')).toBeInTheDocument();
    });
  });

  it('auto-sends initialPrompt in vibe mode', async () => {
    (api.stream as ReturnType<typeof vi.fn>).mockImplementation((_path, _body, signal) =>
      makeAsyncIterator([{ type: 'done' }], signal)
    );

    render(
      <AgentChat
        projectId="p1"
        mode="vibe"
        initialPrompt="make a vibe video"
        onStatusChange={() => {}}
      />
    );

    await waitFor(() => {
      expect(api.stream).toHaveBeenCalledWith(
        '/projects/p1/agent/vibe/stream',
        { message: 'make a vibe video' },
        expect.any(AbortSignal)
      );
    });
  });

  it('calls onStatusChange generating on job_created event', async () => {
    const onStatusChange = vi.fn();
    (api.stream as ReturnType<typeof vi.fn>).mockImplementation((_path, _body, signal) =>
      makeAsyncIterator([{ type: 'job_created', job_id: 'job-1', status: 'queued' }, { type: 'done' }], signal)
    );

    render(<AgentChat projectId="p1" mode="vibe" onStatusChange={onStatusChange} />);

    const input = screen.getByPlaceholderText('描述你的 Vibe 视频想法…');
    fireEvent.change(input, { target: { value: 'test' } });
    fireEvent.submit(input.closest('form')!);

    await waitFor(() => {
      expect(onStatusChange).toHaveBeenCalledWith('generating');
    });
  });

  it('calls onAgentStateChange with artifact payload', async () => {
    const onAgentStateChange = vi.fn();
    const artifact = { kind: 'understand', data: { summary: 'A promo' } };

    (api.stream as ReturnType<typeof vi.fn>).mockImplementation((_path, _body, signal) =>
      makeAsyncIterator([{ type: 'artifact', artifact }, { type: 'done' }], signal)
    );

    render(
      <AgentChat
        projectId="p1"
        mode="vibe"
        onStatusChange={() => {}}
        onAgentStateChange={onAgentStateChange}
      />
    );

    const input = screen.getByPlaceholderText('描述你的 Vibe 视频想法…');
    fireEvent.change(input, { target: { value: 'test' } });
    fireEvent.submit(input.closest('form')!);

    await waitFor(() => {
      expect(onAgentStateChange).toHaveBeenCalledWith(
        expect.objectContaining({
          step: 'understand',
          payload: { understand: { summary: 'A promo' } },
        })
      );
    });
  });

  it('calls onAgentStateChange with done payload', async () => {
    const onAgentStateChange = vi.fn();
    const payload = { script: { title: 'Final' } };

    (api.stream as ReturnType<typeof vi.fn>).mockImplementation((_path, _body, signal) =>
      makeAsyncIterator([{ type: 'done', payload }], signal)
    );

    render(
      <AgentChat
        projectId="p1"
        mode="vibe"
        onStatusChange={() => {}}
        onAgentStateChange={onAgentStateChange}
      />
    );

    const input = screen.getByPlaceholderText('描述你的 Vibe 视频想法…');
    fireEvent.change(input, { target: { value: 'test' } });
    fireEvent.submit(input.closest('form')!);

    await waitFor(() => {
      expect(onAgentStateChange).toHaveBeenLastCalledWith(
        expect.objectContaining({
          step: 'approved',
          payload,
        })
      );
    });
  });

  it('aborts the previous vibe stream when a new message is submitted', async () => {
    const signals: AbortSignal[] = [];
    (api.stream as ReturnType<typeof vi.fn>).mockImplementation((_path, _body, signal) => {
      signals.push(signal as AbortSignal);
      return makeHangingIterator(signal);
    });

    render(<AgentChat projectId="p1" mode="vibe" onStatusChange={() => {}} />);

    const input = screen.getByPlaceholderText('描述你的 Vibe 视频想法…');
    fireEvent.change(input, { target: { value: 'first' } });
    fireEvent.submit(input.closest('form')!);

    await waitFor(() => {
      expect(api.stream).toHaveBeenCalledTimes(1);
    });

    fireEvent.change(input, { target: { value: 'second' } });
    fireEvent.submit(input.closest('form')!);

    await waitFor(() => {
      expect(api.stream).toHaveBeenCalledTimes(2);
    });

    expect(signals[0].aborted).toBe(true);
    expect(signals[1].aborted).toBe(false);
  });

  it('aborts the in-flight vibe stream on unmount', async () => {
    const signals: AbortSignal[] = [];
    (api.stream as ReturnType<typeof vi.fn>).mockImplementation((_path, _body, signal) => {
      signals.push(signal as AbortSignal);
      return makeHangingIterator(signal);
    });

    const { unmount } = render(<AgentChat projectId="p1" mode="vibe" onStatusChange={() => {}} />);

    const input = screen.getByPlaceholderText('描述你的 Vibe 视频想法…');
    fireEvent.change(input, { target: { value: 'first' } });
    fireEvent.submit(input.closest('form')!);

    await waitFor(() => {
      expect(api.stream).toHaveBeenCalledTimes(1);
    });

    unmount();

    await waitFor(() => {
      expect(signals[0].aborted).toBe(true);
    });
  });
});
