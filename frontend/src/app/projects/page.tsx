'use client';

import { AuthGuard } from '@/components/layout/AuthGuard';
import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';

export default function ProjectsPage() {
  return (
    <AuthGuard>
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="flex-1 flex flex-col">
          <TopBar title="项目" />
          <main className="flex-1 p-6">
            <p className="text-slate-600">项目列表</p>
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}
