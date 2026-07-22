'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { useAuthStore } from '@/stores/authStore';
import { Project } from '@/lib/types';
import {
  extractDuration,
  extractFormat,
  extractUrl,
  makeProjectTitle,
} from '@/lib/projectIntent';

const QUICK_TIPS = [
  '从公众号文章生成视频',
  '商品详情页转营销短片',
  '生日祝福视频',
];

export default function HomePage() {
  const router = useRouter();
  const [prompt, setPrompt] = useState('');
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || creating) return;

    // 未登录时 /auth/me 会 401，直接跳转登录页，避免后续 /projects/ 调用触发错误横幅。
    try {
      const me = await api.get('/auth/me');
      if (me?.user) {
        useAuthStore.setState({ user: me.user });
      }
    } catch {
      router.push('/login');
      return;
    }

    setCreating(true);
    setError(null);
    try {
      const sourceUrl = extractUrl(prompt);
      const project = await api.post('/projects/', {
        title: makeProjectTitle(prompt),
        source_url: sourceUrl || '',
        source_type: 'url',
        target_format: extractFormat(prompt),
        target_duration: extractDuration(prompt),
      });
      router.push(`/projects/${project.id}?initialPrompt=${encodeURIComponent(prompt)}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建项目失败');
      setCreating(false);
    }
  };

  return (
    <main className="min-h-dvh bg-background-base text-content-primary flex flex-col">
      <nav className="flex items-center justify-between px-6 py-4 border-b border-border-subtle">
        <span className="font-bold text-lg">ClipWorks</span>
        <div className="flex items-center gap-4 text-sm text-content-secondary">
          <Link href="/projects" className="focus-ring hover:text-content-primary">
            Projects
          </Link>
          <Link href="/billing" className="focus-ring hover:text-content-primary">
            Billing
          </Link>
          <Link href="/settings" className="focus-ring hover:text-content-primary">
            Settings
          </Link>
        </div>
      </nav>

      <div className="flex-1 flex flex-col items-center justify-center px-4 py-8">
        <h1 className="text-3xl md:text-5xl font-bold text-center mb-3">一句话，一条成片</h1>
        <p className="text-content-secondary text-center mb-8 max-w-md">
          描述你的视频，或粘贴链接、上传素材。AI 导演会帮你规划脚本、准备素材并生成视频。
        </p>

        <form onSubmit={handleSubmit} className="w-full max-w-2xl">
          <div className="bg-background-surface border border-border-subtle rounded-2xl p-4 shadow-lg">
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="例如：帮我做一个 15 秒的产品介绍视频，突出 AI 剪辑和省钱的卖点，9:16 竖屏"
              className="focus-ring w-full bg-transparent resize-none outline-none text-lg min-h-[120px] placeholder:text-content-tertiary rounded-md"
            />
            <div className="flex items-center justify-end mt-4">
              <Button type="submit" disabled={!prompt.trim() || creating}>
                {creating ? '创建中…' : '生成视频 →'}
              </Button>
            </div>
          </div>
        </form>

        {error && (
          <div
            data-testid="homepage-error"
            className="mt-4 text-sm text-error bg-error/10 border border-error/20 rounded-lg px-4 py-3 max-w-2xl w-full"
          >
            {error}
          </div>
        )}

        <div className="flex flex-wrap justify-center gap-2 mt-6">
          {QUICK_TIPS.map((tip) => (
            <button
              key={tip}
              type="button"
              onClick={() => setPrompt(tip)}
              className="focus-ring text-sm px-3 py-1.5 rounded-full bg-background-elevated text-content-secondary hover:text-content-primary border border-border-subtle"
            >
              {tip}
            </button>
          ))}
        </div>

        <RecentProjects />
      </div>
    </main>
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
        // 静默隐藏最近项目，避免 API 失败时展示假数据。
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
      <div className="w-full max-w-2xl mt-8">
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
    <div className="w-full max-w-2xl mt-8" data-testid="recent-projects">
      <div className="text-sm text-content-secondary mb-3 px-1">最近项目</div>
      <div className="flex gap-3 overflow-x-auto pb-2">
        {projects.map((p, idx) => (
          <Link
            key={p.id}
            href={`/projects/${p.id}`}
            className="focus-ring min-w-[200px] bg-background-surface border border-border-subtle rounded-lg p-3 hover:border-border-default transition-colors"
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
          </Link>
        ))}
      </div>
    </div>
  );
}
