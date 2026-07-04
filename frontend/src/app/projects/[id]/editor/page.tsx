'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { AuthGuard } from '@/components/layout/AuthGuard';
import { Timeline } from '@/components/editor/Timeline';
import { PreviewPlayer } from '@/components/project/PreviewPlayer';
import { Composition, Project } from '@/lib/types';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { ArrowLeft, Save } from 'lucide-react';
import { getDemoProjectById, getDemoComposition } from '@/lib/demoData';

export default function EditorPage() {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [composition, setComposition] = useState<Composition | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const [projectData, compositionData] = await Promise.all([
          api.get(`/projects/${id}`),
          api.get(`/compositions/${id}`),
        ]);
        if (!cancelled) {
          setProject(projectData);
          setComposition(compositionData.error ? null : compositionData);
        }
      } catch (err) {
        if (!cancelled) {
          // Fallback to demo data for prototype
          const demoProject = getDemoProjectById(id);
          if (demoProject) {
            setProject(demoProject);
            setComposition(getDemoComposition(id));
          } else {
            setError(err instanceof Error ? err.message : '加载编辑器失败');
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
            <p className="text-sm">加载编辑器中…</p>
          </div>
        </div>
      </AuthGuard>
    );
  }

  if (error || !project || !composition) {
    return (
      <AuthGuard>
        <div className="min-h-screen flex items-center justify-center bg-background-base">
          <div className="text-center max-w-md">
            <p className="text-error mb-4">{error || '项目或合成信息不存在'}</p>
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
          <TopBar title={`${project.title} - 时间线编辑器`} />
          <main className="flex-1 p-5 flex flex-col gap-4 overflow-hidden">
            <div className="flex items-center justify-between">
              <Link
                href={`/projects/${id}`}
                className="text-sm text-content-secondary hover:text-content-primary flex items-center gap-1 transition-colors"
              >
                <ArrowLeft className="w-4 h-4" /> 返回工作区
              </Link>
              <Button variant="secondary" size="sm" onClick={() => alert('保存功能在正式版中实现')}>
                <Save className="w-4 h-4 mr-1.5" /> 保存
              </Button>
            </div>
            <div className="h-80 bg-black rounded-md overflow-hidden shrink-0">
              <PreviewPlayer />
            </div>
            <div className="flex-1 overflow-auto min-h-0">
              <Timeline composition={composition} />
            </div>
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}
