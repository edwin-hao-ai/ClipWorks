'use client';

import { useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/Button';
import { api } from '@/lib/api';
import { Project } from '@/lib/types';
import { MessageSquare, Send, Bot, User } from 'lucide-react';

interface Message {
  role: 'user' | 'agent';
  text: string;
}

interface Props {
  projectId: string;
  status: Project['status'];
  onStatusChange: (status: Project['status']) => void;
}

export function AgentChat({ projectId, status, onStatusChange }: Props) {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'agent', text: 'Hi! I can help you refine your video. Try "make the title red" or "shorten scene 2".' },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || loading) return;
    setMessages((prev) => [...prev, { role: 'user', text }]);
    setInput('');
    setLoading(true);
    setError(null);

    try {
      const data = await api.post(`/projects/${projectId}/agent/chat`, { message: text, render: true });
      const reply = data.reply || 'Updated the video.';
      setMessages((prev) => [...prev, { role: 'agent', text: reply }]);
      if (data.job_id) {
        onStatusChange('generating');
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Agent request failed';
      setError(msg);
      setMessages((prev) => [...prev, { role: 'agent', text: `Sorry, I couldn't apply that change: ${msg}` }]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  const quickPrompts = [
    '更活泼一点',
    '针对年轻人',
    '把标题改成红色',
    '缩短第2个场景',
  ];

  return (
    <div className="bg-background-surface border border-border-subtle rounded-md p-5 flex flex-col h-[420px]">
      <h3 className="font-semibold text-content-primary mb-4 flex items-center gap-2 shrink-0">
        <MessageSquare className="w-4 h-4 text-brand-400" /> AI 助手
      </h3>

      <div className="flex-1 overflow-y-auto space-y-3 pr-1 mb-3 min-h-0">
        {messages.map((m, idx) => (
          <div
            key={idx}
            className={`flex gap-2 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}
          >
            <div
              className={`w-7 h-7 rounded-full flex items-center justify-center shrink-0 ${
                m.role === 'agent' ? 'bg-brand-900/50 text-brand-400' : 'bg-background-elevated text-content-secondary'
              }`}
            >
              {m.role === 'agent' ? <Bot className="w-3.5 h-3.5" /> : <User className="w-3.5 h-3.5" />}
            </div>
            <div
              className={`max-w-[80%] text-sm px-3 py-2 rounded-lg ${
                m.role === 'agent'
                  ? 'bg-background-elevated text-content-secondary border border-border-subtle'
                  : 'bg-brand-600 text-content-inverse'
              }`}
            >
              {m.text}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex gap-2">
            <div className="w-7 h-7 rounded-full bg-brand-900/50 text-brand-400 flex items-center justify-center shrink-0">
              <Bot className="w-3.5 h-3.5" />
            </div>
            <div className="bg-background-elevated border border-border-subtle text-content-secondary text-sm px-3 py-2 rounded-lg flex items-center gap-2">
              <span className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce" />
              <span className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce [animation-delay:0.1s]" />
              <span className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce [animation-delay:0.2s]" />
            </div>
          </div>
        )}
        {status === 'generating' && (
          <div className="text-xs text-warning bg-warning/10 border border-warning/20 px-3 py-2 rounded-lg">
            正在根据您的要求重新生成视频…
          </div>
        )}
        {error && (
          <div className="text-xs text-error bg-error/10 border border-error/20 px-3 py-2 rounded-lg">
            {error}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="shrink-0 space-y-2">
        <div className="flex flex-wrap gap-1.5">
          {quickPrompts.map((p) => (
            <button
              key={p}
              onClick={() => sendMessage(p)}
              disabled={loading}
              className="text-xs px-2 py-1 rounded-full bg-background-elevated border border-border-subtle text-content-secondary hover:text-content-primary hover:border-border-default transition-colors disabled:opacity-50"
            >
              {p}
            </button>
          ))}
        </div>
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="输入修改指令…"
            disabled={loading}
            className="flex-1 min-w-0 bg-background-elevated border border-border-subtle rounded-md px-3 py-2 text-sm text-content-primary placeholder-content-tertiary focus:outline-none focus:border-brand-500 disabled:opacity-50"
          />
          <Button type="submit" disabled={loading || !input.trim()} size="sm">
            <Send className="w-4 h-4" />
          </Button>
        </form>
      </div>
    </div>
  );
}
