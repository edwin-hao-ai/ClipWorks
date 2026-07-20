'use client';

import { useEffect, useMemo, useState } from 'react';
import { Film, Search } from 'lucide-react';
import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { AuthGuard } from '@/components/layout/AuthGuard';
import { ProjectCard } from '@/components/project/ProjectCard';
import { NewProjectDialog } from '@/components/project/NewProjectDialog';
import { Project } from '@/lib/types';
import { api } from '@/lib/api';

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [error, setError] = useState<string | null>(null);
  // 首屏加载态：fetch 未完成前展示骨架屏，避免闪一下“空状态”误导老用户。
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<string>('all');
  // 项目数可能很大（测试账号 600+），分页渲染避免一次性挂载几百张卡片。
  const PAGE_SIZE = 60;
  const [visibleCount, setVisibleCount] = useState(PAGE_SIZE);

  const STATUS_LABEL: Record<string, string> = {
    all: '全部',
    draft: '草稿',
    planning: '规划中',
    generating: '生成中',
    ready: '已完成',
    failed: '失败',
  };
  const STATUS_ORDER = ['all', 'draft', 'planning', 'generating', 'ready', 'failed'];

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return projects.filter((p) => {
      const matchesQuery = !q || p.title.toLowerCase().includes(q);
      const matchesStatus = statusFilter === 'all' || p.status === statusFilter;
      return matchesQuery && matchesStatus;
    });
  }, [projects, query, statusFilter]);

  const load = async () => {
    setError(null);
    try {
      const data = await api.get('/projects/');
      setProjects(Array.isArray(data) ? data : []);
    } catch (err) {
      setProjects([]);
      setError(err instanceof Error ? err.message : '加载项目失败');
    } finally {
      setLoading(false);
    }
  };

  const deleteProject = async (id: string) => {
    try {
      await api.delete(`/projects/${id}`);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除项目失败');
    }
  };

  useEffect(() => {
    load();
  }, []);

  // 从工作区/素材库等页面（或浏览器其他标签页）返回时状态可能已变化，
  // 标签页重新可见时静默刷新一次，避免列表长期显示陈旧的「生成中」。
  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState === 'visible') load();
    };
    document.addEventListener('visibilitychange', onVisible);
    return () => document.removeEventListener('visibilitychange', onVisible);
  }, []);

  // 搜索/筛选变化时重置分页，避免结果集变小后还停在深分页。
  useEffect(() => {
    setVisibleCount(PAGE_SIZE);
  }, [query, statusFilter]);

  const visible = filtered.slice(0, visibleCount);

  return (
    <AuthGuard>
      <div className="flex min-h-dvh bg-background-base">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <TopBar title="我的项目" />
          <main id="cw-main" className="flex-1 p-6 overflow-auto">
            <div className="flex justify-between items-center mb-6">
              <div>
                <h2 className="text-2xl font-bold text-content-primary">全部项目</h2>
                <p className="text-sm text-content-secondary mt-1">管理和生成你的 AI 视频项目</p>
              </div>
              <NewProjectDialog onCreated={load} />
            </div>
            {projects.length > 0 && (
              <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="relative sm:w-72">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-content-tertiary" />
                  <input
                    data-testid="project-search"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="搜索项目标题…"
                    className="w-full pl-9 pr-3 py-2 rounded-md bg-background-surface border border-border-subtle text-sm text-content-primary placeholder:text-content-tertiary focus:outline-none focus:border-brand-500"
                  />
                </div>
                <div className="flex items-center gap-1.5 flex-wrap">
                  {STATUS_ORDER.map((key) => (
                    <button
                      key={key}
                      type="button"
                      data-testid={`status-filter-${key}`}
                      onClick={() => setStatusFilter(key)}
                      className={`focus-ring px-2.5 py-1 rounded-full text-xs font-medium transition-colors ${
                        statusFilter === key
                          ? 'bg-brand-600 text-white'
                          : 'bg-background-surface border border-border-subtle text-content-secondary hover:border-border-default'
                      }`}
                    >
                      {STATUS_LABEL[key]}
                    </button>
                  ))}
                  <span className="ml-1 text-xs text-content-tertiary">
                    {filtered.length === projects.length
                      ? `共 ${projects.length} 项`
                      : `${filtered.length} / 共 ${projects.length} 项`}
                  </span>
                </div>
              </div>
            )}
            {error && (
              <div className="mb-4 text-sm text-warning bg-warning/10 border border-warning/20 rounded-md px-4 py-3">
                {error}
              </div>
            )}
            {loading ? (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {Array.from({ length: 6 }).map((_, i) => (
                  <div
                    key={i}
                    className="bg-background-surface border border-border-subtle rounded-md overflow-hidden"
                  >
                    <div className="aspect-video bg-background-elevated animate-pulse" />
                    <div className="p-4 space-y-3">
                      <div className="h-4 w-3/4 rounded bg-background-elevated animate-pulse" />
                      <div className="h-3 w-1/2 rounded bg-background-elevated animate-pulse" />
                    </div>
                  </div>
                ))}
              </div>
            ) : projects.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-24 bg-background-surface border border-border-subtle rounded-lg text-content-secondary">
                <Film className="w-16 h-16 mb-4 text-content-tertiary" />
                <p className="text-lg font-medium text-content-primary mb-2">开始你的第一个视频项目</p>
                <p className="text-sm text-content-secondary mb-6">输入官网链接或上传素材，让 AI 为你生成成片</p>
                <NewProjectDialog onCreated={load} />
              </div>
            ) : filtered.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-20 bg-background-surface border border-border-subtle rounded-lg text-content-secondary">
                <Search className="w-12 h-12 mb-3 text-content-tertiary" />
                <p className="text-base font-medium text-content-primary mb-1">没有匹配的项目</p>
                <p className="text-sm text-content-secondary">换个关键词或重置筛选条件试试</p>
              </div>
            ) : (
              <>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {visible.map((project) => (
                    <ProjectCard key={project.id} project={project} onDelete={deleteProject} />
                  ))}
                </div>
                {filtered.length > visibleCount && (
                  <div className="mt-8 flex justify-center">
                    <button
                      type="button"
                      onClick={() => setVisibleCount((n) => n + PAGE_SIZE)}
                      className="px-5 py-2.5 rounded-md border border-border-default text-sm font-medium text-content-secondary hover:text-content-primary hover:bg-background-hover transition-colors duration-150"
                    >
                      加载更多（剩余 {filtered.length - visibleCount} 个）
                    </button>
                  </div>
                )}
              </>
            )}
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}
