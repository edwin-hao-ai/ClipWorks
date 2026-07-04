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

export default function EditorPage() {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [composition, setComposition] = useState<Composition | null>(null);

  useEffect(() => {
    api.get(`/projects/${id}`).then(setProject);
    api.get(`/compositions/${id}`).then((data) => {
      if (!data.error) setComposition(data);
    });
  }, [id]);

  if (!project || !composition) {
    return (
      <AuthGuard>
        <div className="min-h-screen flex items-center justify-center">加载中…</div>
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
