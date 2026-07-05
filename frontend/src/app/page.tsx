'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Sparkles } from 'lucide-react';
import { clsx } from 'clsx';
import { LaunchNav } from '@/components/layout/LaunchNav';
import { Button } from '@/components/ui/Button';
import { api } from '@/lib/api';

const QUICK_PROMPTS = [
  '小红书口播精剪',
  'SaaS 产品发布',
  '教程视频',
  '短视频广告',
  '生日祝福视频',
];

export default function HomePage() {
  const router = useRouter();
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createProject = async (input: string) => {
    if (!input.trim() || loading) return;
    setLoading(true);
    setError(null);
    try {
      const project = await api.post('/projects/', {
        title: input.slice(0, 40) || '未命名项目',
        source_url: '',
        source_type: 'url',
      });
      router.push(`/projects/${project.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建项目失败');
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createProject(prompt);
  };

  return (
    <div className="min-h-screen bg-background-base flex flex-col relative overflow-hidden">
      <LaunchNav />
      <main className="flex-1 flex flex-col items-center justify-center px-6 relative">
        <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none">
          <div className="absolute -top-1/2 -left-1/4 w-[700px] h-[700px] rounded-full bg-brand-900/25 blur-[140px]" />
          <div className="absolute -bottom-1/4 -right-1/4 w-[600px] h-[600px] rounded-full bg-purple-900/15 blur-[120px]" />
        </div>

        <div className="relative text-center max-w-3xl w-full">
          <h1 className="text-4xl md:text-5xl font-bold mb-5 tracking-tight">
            一句话，一段素材，一条成片
          </h1>
          <p className="text-text-secondary text-lg mb-10">
            告诉 AI 你想做什么视频，它会自动规划、剪辑、出片。
          </p>

          <form onSubmit={handleSubmit} className="mb-6">
            <div className="bg-background-elevated border border-border-default rounded-2xl p-2 flex items-center gap-2 shadow-glow focus-within:border-brand-500 transition-colors">
              <input
                type="text"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="例如：帮我做一个 30 秒的产品介绍视频，风格活泼，面向年轻人…"
                className="flex-1 bg-transparent px-4 py-3 text-base outline-none placeholder-text-tertiary text-left"
                disabled={loading}
              />
              <Button
                type="submit"
                disabled={loading || !prompt.trim()}
                size="lg"
                className="shrink-0"
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    创建中
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4" />
                    开始创作
                  </span>
                )}
              </Button>
            </div>
          </form>

          {error && (
            <div className="mb-6 text-sm text-error bg-error/10 border border-error/20 rounded-lg px-4 py-3">
              {error}
            </div>
          )}

          <div className="flex flex-wrap justify-center gap-2 mb-16">
            <span className="text-sm text-text-tertiary py-1.5">热门：</span>
            {QUICK_PROMPTS.map((p) => (
              <button
                key={p}
                onClick={() => createProject(p)}
                disabled={loading}
                className="px-3 py-1.5 rounded-full bg-background-elevated border border-border-subtle text-sm text-text-secondary hover:border-brand-500/50 hover:text-brand-400 transition-colors disabled:opacity-50"
              >
                {p}
              </button>
            ))}
          </div>

          <RecentProjects />
        </div>
      </main>
    </div>
  );
}

function RecentProjects() {
  const projects = [
    { id: '1', title: '产品发布视频', time: '2 小时前', status: '已完成', gradient: 'from-blue-600/40 to-purple-600/40' },
    { id: '2', title: '小红书口播', time: '昨天', status: '草稿', gradient: 'from-pink-600/40 to-orange-600/40' },
    { id: '3', title: '功能更新说明', time: '3 天前', status: '已完成', gradient: 'from-emerald-600/40 to-teal-600/40' },
  ];

  return (
    <div className="text-left">
      <div className="text-sm text-text-secondary mb-3 px-1">最近项目</div>
      <div className="flex gap-3 overflow-x-auto pb-2">
        {projects.map((p) => (
          <a
            key={p.id}
            href={`/projects/${p.id}`}
            className="min-w-[200px] bg-background-surface border border-border-subtle rounded-lg p-3 hover:border-border-default transition-colors"
          >
            <div className={clsx('aspect-video rounded-md bg-gradient-to-br mb-2', p.gradient)} />
            <div className="text-sm font-medium text-content-primary truncate">{p.title}</div>
            <div className="flex items-center justify-between mt-1">
              <span className="text-xs text-text-tertiary">{p.time}</span>
              <span className="text-xs text-success">{p.status}</span>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}
