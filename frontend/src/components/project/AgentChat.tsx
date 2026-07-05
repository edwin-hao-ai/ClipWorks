'use client';

import { useEffect, useRef, useState } from 'react';
import { clsx } from 'clsx';
import { Button } from '@/components/ui/Button';
import { api } from '@/lib/api';
import { Scene } from '@/lib/types';
import { MessageSquare, Send, Bot, User, Pencil } from 'lucide-react';

interface Message {
  role: 'user' | 'agent';
  text: string;
}

interface AgentChatProps {
  projectId: string;
  status: string;
  selectedSceneId?: string | null;
  scenes?: Scene[];
  onStatusChange: (status: 'draft' | 'generating' | 'ready' | 'failed') => void;
}

const QUICK_PROMPTS = [
  '更活泼一点',
  '针对年轻人',
  '把标题改成红色',
  '缩短到 15 秒',
  '换背景音乐',
];

export function AgentChat({ projectId, status, selectedSceneId, scenes = [], onStatusChange }: AgentChatProps) {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'agent', text: 'Hi! 我是你的 AI 导演。输入一句话开始创作，或点击左侧场景卡片修改某个画面。' },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const selectedScene = scenes.find((s) => s.id === selectedSceneId);

  useEffect(() => {
    if (selectedScene) {
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last?.role === 'agent' && last.text.includes(`「${selectedScene.name}」`)) return prev;
        return [
          ...prev,
          { role: 'agent', text: `你选中了「${selectedScene.name}」（${formatTime(selectedScene.start_time)}-${formatTime(selectedScene.start_time + selectedScene.duration)}）。想怎么改这个场景？` },
        ];
      });
    }
  }, [selectedSceneId, scenes]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || loading) return;
    setMessages((prev) => [...prev, { role: 'user', text }]);
    setInput('');
    setLoading(true);
    setError(null);

    try {
      const payload: Record<string, any> = { message: text, render: true };
      if (selectedSceneId) payload.scene_id = selectedSceneId;
      const data = await api.post(`/projects/${projectId}/agent/chat`, payload);
      const reply = data.reply || '已收到你的修改要求。';
      setMessages((prev) => [...prev, { role: 'agent', text: reply }]);
      if (data.job_id) {
        onStatusChange('generating');
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Agent 请求失败';
      setError(msg);
      setMessages((prev) => [...prev, { role: 'agent', text: `抱歉，我没法应用这个修改：${msg}` }]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  return (
    <div className="bg-background-surface border border-border-subtle rounded-lg p-4 flex flex-col h-[360px]">
      <div className="flex items-center gap-2 mb-3 shrink-0">
        <MessageSquare className="w-4 h-4 text-brand-400" />
        <span className="text-sm font-semibold">AI 导演</span>
        {selectedScene && (
          <span className="ml-auto text-xs px-2 py-0.5 rounded-full bg-brand-900/40 text-brand-400 border border-brand-900/60 flex items-center gap-1">
            <Pencil className="w-3 h-3" /> {selectedScene.name}
          </span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto space-y-3 pr-1 mb-3 min-h-0 text-sm">
        {messages.map((m, idx) => (
          <div key={idx} className={`flex gap-2 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
            <div
              className={clsx(
                'w-7 h-7 rounded-full flex items-center justify-center shrink-0',
                m.role === 'agent' ? 'bg-brand-900/50 text-brand-400' : 'bg-background-elevated text-content-secondary'
              )}
            >
              {m.role === 'agent' ? <Bot className="w-3.5 h-3.5" /> : <User className="w-3.5 h-3.5" />}
            </div>
            <div
              className={clsx(
                'max-w-[85%] text-sm px-3 py-2 rounded-lg',
                m.role === 'agent'
                  ? 'bg-background-elevated text-content-secondary border border-border-subtle'
                  : 'bg-brand-600 text-content-inverse'
              )}
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
            <div className="bg-background-elevated border border-border-subtle text-content-secondary text-sm px-3 py-2 rounded-lg flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce" />
              <span className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce [animation-delay:0.1s]" />
              <span className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce [animation-delay:0.2s]" />
            </div>
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
          {QUICK_PROMPTS.map((p) => (
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
            placeholder={selectedScene ? `修改「${selectedScene.name}」…` : '输入创作或修改指令…'}
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

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}
