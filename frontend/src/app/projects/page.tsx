'use client';

import { useEffect, useState } from 'react';
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

  const load = async () => {
    setError(null);
    try {
      const data = await api.get('/projects/');
      setProjects(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载项目失败');
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

  return (
    <AuthGuard>
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="flex-1 flex flex-col">
          <TopBar title="我的项目" />
          <main className="flex-1 p-8">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-semibold text-slate-900">全部项目</h2>
              <NewProjectDialog onCreated={load} />
            </div>
            {error && (
              <div className="mb-4 text-sm text-red-700 bg-red-50 border border-red-100 rounded-lg px-4 py-3">
                {error}
              </div>
            )}
            {projects.length === 0 ? (
              <div className="text-center py-20 text-slate-500 bg-white rounded-xl border border-slate-200">
                还没有项目，点击右上角「新建项目」开始
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
