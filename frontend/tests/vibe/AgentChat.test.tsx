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

function makeAsyncIterator<T>(items: T[]): AsyncIterableIterator<T> {
  let idx = 0;
  return {
    [Symbol.asyncIterator]() {
      return this;
    },
    async next() {
      if (idx < items.length) {
        return { value: items[idx++], done: false };
      }
      return { value: undefined, done: true };
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
    (api.stream as ReturnType<typeof vi.fn>).mockReturnValue(makeAsyncIterator([{ type: 'done' }]));

    render(<AgentChat projectId="p1" mode="vibe" onStatusChange={() => {}} />);

    const input = screen.getByPlaceholderText('描述你的 Vibe 视频想法…');
    fireEvent.change(input, { target: { value: 'make a promo' } });
    fireEvent.submit(input.closest('form')!);

    await waitFor(() => {
      expect(api.stream).toHaveBeenCalledWith('/projects/p1/agent/vibe/stream', {
        message: 'make a promo',
      });
    });
  });

  it('appends token events to streaming text', async () => {
    (api.stream as ReturnType<typeof vi.fn>).mockReturnValue(
      makeAsyncIterator([
        { type: 'token', token: 'Hello' },
        { type: 'token', token: ' world' },
        { type: 'done' },
      ])
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
    (api.stream as ReturnType<typeof vi.fn>).mockReturnValue(
      makeAsyncIterator([{ type: 'question', question: 'Which format?' }, { type: 'done' }])
    );

    render(<AgentChat projectId="p1" mode="vibe" onStatusChange={() => {}} />);

    const input = screen.getByPlaceholderText('描述你的 Vibe 视频想法…');
    fireEvent.change(input, { target: { value: 'test' } });
    fireEvent.submit(input.closest('form')!);

    await waitFor(() => {
      expect(screen.getByText('Which format?')).toBeInTheDocument();
    });
  });

  it('calls onAgentStateChange with artifact payload', async () => {
    const onAgentStateChange = vi.fn();
    const artifact = { kind: 'understand', data: { summary: 'A promo' } };

    (api.stream as ReturnType<typeof vi.fn>).mockReturnValue(
      makeAsyncIterator([{ type: 'artifact', artifact }, { type: 'done' }])
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

    (api.stream as ReturnType<typeof vi.fn>).mockReturnValue(
      makeAsyncIterator([{ type: 'done', payload }])
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
});
