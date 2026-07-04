'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { AuthGuard } from '@/components/layout/AuthGuard';
import { GenerationPanel } from '@/components/project/GenerationPanel';
import { AgentChat } from '@/components/project/AgentChat';
import { ScriptPanel } from '@/components/project/ScriptPanel';
import { PreviewPlayer } from '@/components/project/PreviewPlayer';
import { DownloadButtons } from '@/components/project/DownloadButtons';
import { Button } from '@/components/ui/Button';
import { Project, RenderJob } from '@/lib/types';
import { api } from '@/lib/api';
import { Film, Layers, Image, ArrowLeft } from 'lucide-react';
import { getDemoProjectById } from '@/lib/demoData';

export default function ProjectWorkspacePage() {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [job, setJob] = useState<RenderJob | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await api.get(`/projects/${id}`);
        if (!cancelled) {
          setProject(data);
        }
      } catch (err) {
        if (!cancelled) {
          // Fallback to demo project for prototype
          const demo = getDemoProjectById(id);
          if (demo) {
            setProject(demo);
          } else {
            setError(err instanceof Error ? err.message : '加载项目失败');
          }
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    load();

    return () => {
      cancelled = true;
    };
  }, [id]);

  if (loading) {
    return (
      <AuthGuard>
        <div className="min-h-screen flex items-center justify-center bg-background-base text-content-secondary">
          <div className="flex flex-col items-center gap-4">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500" />
            <p className="text-sm">加载项目中…</p>
          </div>
        </div>
      </AuthGuard>
    );
  }

  if (error || !project) {
    return (
      <AuthGuard>
        <div className="min-h-screen flex items-center justify-center bg-background-base">
          <div className="text-center max-w-md">
            <p className="text-error mb-4">{error || '项目不存在'}</p>
            <Button onClick={() => window.location.reload()}>重试</Button>
          </div>
        </div>
      </AuthGuard>
    );
  }

  return (
    <AuthGuard>
      <div className="flex min-h-screen bg-background-base">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <TopBar title={project.title} />
          <main className="flex-1 p-6 overflow-hidden">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-[calc(100vh-5.5rem)]">
              {/* Left panel */}
              <div className="lg:col-span-4 xl:col-span-3 space-y-5 overflow-auto pr-1">
                <GenerationPanel
                  projectId={project.id}
                  status={project.status}
                  onStatusChange={(s) => setProject({ ...project, status: s })}
                  onJobComplete={(j) => setJob(j)}
                />
                <AgentChat
                  projectId={project.id}
                  status={project.status}
                  onStatusChange={(s) => setProject({ ...project, status: s })}
                />
                <ScriptPanel sourceUrl={project.source_url} />
                <div className="bg-background-surface border border-border-subtle rounded-md p-5">
                  <h3 className="font-semibold text-content-primary mb-3">快捷入口</h3>
                  <div className="space-y-2">
                    <Link
                      href={`/projects/${project.id}`}
                      className="flex items-center gap-2 px-3 py-2 rounded-md bg-brand-900/40 text-brand-400 text-sm border border-brand-900/60"
                    >
                      <Film className="w-4 h-4" /> 生成
                    </Link>
                    <Link
                      href={`/projects/${project.id}/editor`}
                      className="flex items-center gap-2 px-3 py-2 rounded-md text-content-secondary hover:bg-background-hover hover:text-content-primary text-sm transition-colors"
                    >
                      <Layers className="w-4 h-4" /> 时间线
                    </Link>
                    <Link
                      href={`/projects/${project.id}/assets`}
                      className="flex items-center gap-2 px-3 py-2 rounded-md text-content-secondary hover:bg-background-hover hover:text-content-primary text-sm transition-colors"
                    >
                      <Image className="w-4 h-4" /> 素材库
                    </Link>
                  </div>
                </div>
              </div>

              {/* Center preview + downloads */}
              <div className="lg:col-span-8 xl:col-span-9 flex flex-col gap-4 min-h-0">
                <div className="flex-1 bg-black rounded-md overflow-hidden min-h-0">
                  <PreviewPlayer videoUrl={job?.output_url || undefined} />
                </div>
                <div className="flex items-center justify-between shrink-0">
                  <Link
                    href="/projects"
                    className="text-sm text-content-secondary hover:text-content-primary flex items-center gap-1 transition-colors"
                  >
                    <ArrowLeft className="w-4 h-4" /> 返回项目列表
                  </Link>
                  <DownloadButtons
                    mp4Url={job?.output_url || undefined}
                    htmlUrl={job?.html_output_url || undefined}
                  />
                </div>
              </div>
            </div>
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}
