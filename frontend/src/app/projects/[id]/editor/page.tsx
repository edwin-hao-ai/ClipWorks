'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { AuthGuard } from '@/components/layout/AuthGuard';
import { Timeline } from '@/components/editor/Timeline';
import { PreviewPlayer } from '@/components/project/PreviewPlayer';
import { Composition, Project } from '@/lib/types';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/Button';

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
          setError(err instanceof Error ? err.message : '加载编辑器失败');
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
        <div className="min-h-screen flex items-center justify-center">加载中…</div>
      </AuthGuard>
    );
  }

  if (error || !project || !composition) {
    return (
      <AuthGuard>
        <div className="min-h-screen flex items-center justify-center">
          <div className="text-center max-w-md">
            <p className="text-red-600 mb-4">{error || '项目或合成信息不存在'}</p>
            <Button onClick={() => window.location.reload()}>重试</Button>
          </div>
        </div>
      </AuthGuard>
    );
  }

  return (
    <AuthGuard>
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="flex-1 flex flex-col">
          <TopBar title={`${project.title} - 时间线编辑器`} />
          <main className="flex-1 p-6 flex flex-col gap-4">
            <div className="h-80 bg-black rounded-xl">
              <PreviewPlayer />
            </div>
            <div className="flex-1 overflow-auto">
              <Timeline composition={composition} />
            </div>
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}
