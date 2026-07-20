'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Sparkles } from 'lucide-react';
import { LaunchNav } from '@/components/layout/LaunchNav';
import { Button } from '@/components/ui/Button';
import { api } from '@/lib/api';
import { Project } from '@/lib/types';
import { useAuthStore } from '@/stores/authStore';
import {
  QUICK_PROMPTS,
  extractDuration,
  extractFormat,
  extractUrl,
  makeProjectTitle,
} from '@/lib/projectIntent';

export default function HomePage() {
  const router = useRouter();
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createProject = async (input: string) => {
    if (!input.trim() || loading) return;
    // 未登录时 /auth/me 会 401（reject），此时直接跳转登录页，避免触发 /projects/ 的 401 错误横幅。
    try {
      const me = await api.get('/auth/me');
      if (me?.user) {
        useAuthStore.setState({ user: me.user });
      }
    } catch {
      router.push('/login');
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const sourceUrl = extractUrl(input);
      const project = await api.post('/projects/', {
        title: makeProjectTitle(input),
        source_url: sourceUrl || '',
        source_type: 'url',
        target_format: extractFormat(input),
        target_duration: extractDuration(input),
      });
      const query = `?initialPrompt=${encodeURIComponent(input)}`;
      router.push(`/projects/${project.id}${query}`);
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
    <div className="min-h-dvh bg-background-base flex flex-col relative overflow-hidden">
      <LaunchNav />
      <main id="cw-main" className="flex-1 flex flex-col items-center justify-center px-6 relative">
        <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none">
          <div className="absolute -top-1/2 -left-1/4 w-[700px] h-[700px] rounded-full bg-brand-900/25 blur-[140px]" />
          <div className="absolute -bottom-1/4 -right-1/4 w-[600px] h-[600px] rounded-full bg-purple-900/15 blur-[120px]" />
        </div>

        <div className="relative text-center max-w-3xl w-full">
          <h1 className="text-4xl md:text-5xl font-bold mb-5 tracking-tight">
            一句话，一段素材，一条成片
          </h1>
          <p className="text-content-secondary text-lg mb-10">
            告诉 AI 你想做什么视频，它会自动规划、剪辑、出片。
          </p>

          <form onSubmit={handleSubmit} className="mb-6">
            <div className="bg-background-elevated border border-border-default rounded-2xl p-2 flex items-center gap-2 shadow-glow focus-within:border-brand-500 transition-colors">
              <input
                type="text"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="例如：帮我做一个 30 秒的产品介绍视频，9:16，风格活泼，面向年轻人…"
                className="flex-1 min-w-0 bg-transparent px-4 py-3 text-base outline-none placeholder-content-tertiary text-left"
                disabled={loading}
              />
              <Button
                type="submit"
                disabled={loading || !prompt.trim()}
                size="lg"
                className="shrink-0 px-3 sm:px-5"
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
            <span className="text-sm text-content-tertiary py-1.5">热门：</span>
            {QUICK_PROMPTS.map((p) => (
              <button
                key={p}
                onClick={() => createProject(p)}
                disabled={loading}
                className="focus-ring px-3 py-1.5 rounded-full bg-background-elevated border border-border-subtle text-sm text-content-secondary hover:border-brand-500/50 hover:text-brand-400 transition-colors disabled:opacity-50"
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
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api
      .get('/projects/')
      .then((data) => {
        if (!cancelled && Array.isArray(data)) {
          setProjects(data.slice(0, 3));
        }
      })
      .catch(() => {
        // Silently hide recent projects on error to avoid showing fake data.
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return (
      <div className="text-left">
        <div className="text-sm text-content-secondary mb-3 px-1">最近项目</div>
        <div className="flex gap-3 overflow-x-auto pb-2">
          {[1, 2, 3].map((i) => (
            <div
              key={i}
              className="min-w-[200px] bg-background-surface border border-border-subtle rounded-lg p-3 animate-pulse"
            >
              <div className="aspect-video rounded-md bg-background-elevated mb-2" />
              <div className="h-4 bg-background-elevated rounded w-3/4 mb-2" />
              <div className="h-3 bg-background-elevated rounded w-1/2" />
            </div>
          ))}
        </div>
      </div>
    );
  }

  if (projects.length === 0) return null;

  const formatTime = (iso?: string) => {
    if (!iso) return '';
    const d = new Date(iso);
    const now = new Date();
    const diff = Math.floor((now.getTime() - d.getTime()) / 1000);
    if (diff < 60) return '刚刚';
    if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`;
    if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`;
    return `${Math.floor(diff / 86400)} 天前`;
  };

  const statusLabel: Record<string, string> = {
    draft: '草稿',
    planning: '规划中',
    generating: '生成中',
    ready: '已完成',
    failed: '失败',
  };

  const statusColor: Record<string, string> = {
    draft: 'text-content-tertiary',
    planning: 'text-brand-400',
    generating: 'text-warning',
    ready: 'text-success',
    failed: 'text-error',
  };

  const gradients = [
    'from-blue-600/40 to-purple-600/40',
    'from-pink-600/40 to-orange-600/40',
    'from-emerald-600/40 to-teal-600/40',
  ];

  return (
    <div className="text-left">
      <div className="text-sm text-content-secondary mb-3 px-1">最近项目</div>
      <div className="flex gap-3 overflow-x-auto pb-2">
        {projects.map((p, idx) => (
          <a
            key={p.id}
            href={`/projects/${p.id}`}
            className="min-w-[200px] bg-background-surface border border-border-subtle rounded-lg p-3 hover:border-border-default transition-colors"
          >
            <div
              className={`aspect-video rounded-md bg-gradient-to-br mb-2 ${gradients[idx % gradients.length]}`}
            />
            <div className="text-sm font-medium text-content-primary truncate">{p.title}</div>
            <div className="flex items-center justify-between mt-1">
              <span className="text-xs text-content-tertiary">{formatTime(p.updated_at)}</span>
              <span className={`text-xs ${statusColor[p.status] || 'text-content-tertiary'}`}>
                {statusLabel[p.status] || p.status}
              </span>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}
