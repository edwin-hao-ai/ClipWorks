'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { AuthGuard } from '@/components/layout/AuthGuard';
import { GenerationPanel } from '@/components/project/GenerationPanel';
import { ScriptPanel } from '@/components/project/ScriptPanel';
import { Button } from '@/components/ui/Button';
import { Project } from '@/lib/types';
import { api } from '@/lib/api';
import { Film, Layers, Image } from 'lucide-react';

export default function ProjectWorkspacePage() {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<Project | null>(null);

  const load = async () => {
    const data = await api.get(`/projects/${id}`);
    setProject(data);
  };

  useEffect(() => {
    load();
  }, [id]);

  if (!project) {
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
          <TopBar title={project.title} />
          <main className="flex-1 p-8">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100vh-8rem)]">
              {/* Left panel */}
              <div className="space-y-6 overflow-auto">
                <GenerationPanel
                  projectId={project.id}
                  status={project.status}
                  onStatusChange={(s) => setProject({ ...project, status: s as any })}
                />
                <ScriptPanel sourceUrl={project.source_url} />
                <div className="bg-white rounded-xl border border-slate-200 p-6">
                  <h3 className="font-semibold text-slate-900 mb-3">快捷入口</h3>
                  <div className="space-y-2">
                    <Link
                      href={`/projects/${project.id}`}
                      className="flex items-center gap-2 px-3 py-2 rounded-lg bg-brand-50 text-brand-700 text-sm"
                    >
                      <Film className="w-4 h-4" /> 生成
                    </Link>
                    <Link
                      href={`/projects/${project.id}?tab=editor`}
                      className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-slate-50 text-slate-700 text-sm"
                    >
                      <Layers className="w-4 h-4" /> 时间线
                    </Link>
                    <Link
                      href={`/projects/${project.id}/assets`}
                      className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-slate-50 text-slate-700 text-sm"
                    >
                      <Image className="w-4 h-4" /> 素材库
                    </Link>
                  </div>
                </div>
              </div>

              {/* Center preview placeholder */}
              <div className="lg:col-span-2 bg-black rounded-xl flex items-center justify-center text-white">
                <div className="text-center">
                  <Film className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p className="opacity-70">视频预览区域</p>
                  {project.status === 'ready' && (
                    <Button variant="secondary" className="mt-4">
                      播放预览
                    </Button>
                  )}
                </div>
              </div>
            </div>
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}
