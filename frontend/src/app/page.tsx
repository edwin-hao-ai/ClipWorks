'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { useAuthStore } from '@/stores/authStore';

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
      const project = await api.post('/projects/', {
        title: prompt.slice(0, 50),
        prompt,
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
          <a href="/projects" className="hover:text-content-primary">Projects</a>
          <a href="/billing" className="hover:text-content-primary">Billing</a>
          <a href="/settings" className="hover:text-content-primary">Settings</a>
        </div>
      </nav>

      <div className="flex-1 flex flex-col items-center justify-center px-4">
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
              className="w-full bg-transparent resize-none outline-none text-lg min-h-[120px] placeholder:text-content-tertiary"
            />
            <div className="flex items-center justify-between mt-4">
              <div className="flex gap-2">
                <button
                  type="button"
                  className="text-sm px-3 py-1.5 rounded-full bg-background-elevated text-content-secondary hover:text-content-primary"
                >
                  📎 素材
                </button>
                <button
                  type="button"
                  className="text-sm px-3 py-1.5 rounded-full bg-background-elevated text-content-secondary hover:text-content-primary"
                >
                  🔗 URL
                </button>
                <button
                  type="button"
                  className="text-sm px-3 py-1.5 rounded-full bg-background-elevated text-content-secondary hover:text-content-primary"
                >
                  🎨 风格
                </button>
              </div>
              <Button type="submit" disabled={!prompt.trim() || creating}>
                {creating ? '创建中…' : '生成视频 →'}
              </Button>
            </div>
          </div>
        </form>

        {error && (
          <div data-testid="homepage-error" className="mt-4 text-sm text-error bg-error/10 border border-error/20 rounded-lg px-4 py-3 max-w-2xl w-full">
            {error}
          </div>
        )}

        <div className="flex flex-wrap justify-center gap-2 mt-6">
          {['从公众号文章生成视频', '商品详情页转营销短片', '生日祝福视频'].map((tip) => (
            <button
              key={tip}
              onClick={() => setPrompt(tip)}
              className="text-sm px-3 py-1.5 rounded-full bg-background-elevated text-content-secondary hover:text-content-primary border border-border-subtle"
            >
              {tip}
            </button>
          ))}
        </div>
      </div>
    </main>
  );
}
