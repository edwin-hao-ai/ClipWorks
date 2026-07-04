'use client';

import { useEffect, useState } from 'react';
import { Film, Plus } from 'lucide-react';
import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { AuthGuard } from '@/components/layout/AuthGuard';
import { ProjectCard } from '@/components/project/ProjectCard';
import { NewProjectDialog } from '@/components/project/NewProjectDialog';
import { Project } from '@/lib/types';
import { api } from '@/lib/api';
import { DEMO_PROJECTS } from '@/lib/demoData';

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setError(null);
    try {
      const data = await api.get('/projects/');
      // Use demo data if API returns empty so the prototype always looks populated
      setProjects(Array.isArray(data) && data.length > 0 ? data : DEMO_PROJECTS);
    } catch (err) {
      setProjects(DEMO_PROJECTS);
      setError(err instanceof Error ? err.message : '加载项目失败');
    }
  };

  const deleteProject = async (id: string) => {
    try {
      await api.delete(`/projects/${id}`);
      load();
    } catch (err) {
      // Optimistically remove from local demo list
      setProjects((prev) => prev.filter((p) => p.id !== id));
    }
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <AuthGuard>
      <div className="flex min-h-screen bg-background-base">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <TopBar title="我的项目" />
          <main className="flex-1 p-6 overflow-auto">
            <div className="flex justify-between items-center mb-6">
              <div>
                <h2 className="text-2xl font-bold text-content-primary">全部项目</h2>
                <p className="text-sm text-content-secondary mt-1">管理和生成你的 AI 视频项目</p>
              </div>
              <NewProjectDialog onCreated={load} />
            </div>
            {error && (
              <div className="mb-4 text-sm text-warning bg-warning/10 border border-warning/20 rounded-md px-4 py-3">
                {error}
              </div>
            )}
            {projects.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-24 bg-background-surface border border-border-subtle rounded-lg text-content-secondary">
                <Film className="w-16 h-16 mb-4 text-content-tertiary" />
                <p className="text-lg font-medium text-content-primary mb-2">开始你的第一个视频项目</p>
                <p className="text-sm text-content-secondary mb-6">输入官网链接或上传素材，让 AI 为你生成成片</p>
                <NewProjectDialog onCreated={load} />
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {projects.map((project) => (
                  <ProjectCard key={project.id} project={project} onDelete={deleteProject} />
                ))}
              </div>
            )}
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}
