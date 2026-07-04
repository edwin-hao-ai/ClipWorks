'use client';

import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { AuthGuard } from '@/components/layout/AuthGuard';
import { useAuthStore } from '@/stores/authStore';

export default function SettingsPage() {
  const user = useAuthStore((s) => s.user);

  return (
    <AuthGuard>
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="flex-1 flex flex-col">
          <TopBar title="设置" />
          <main className="flex-1 p-8">
            <div className="max-w-2xl bg-white rounded-xl border border-slate-200 p-6">
              <h2 className="text-lg font-semibold text-slate-900 mb-6">账户信息</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700">邮箱</label>
                  <p className="mt-1 text-slate-900">{user?.email}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700">昵称</label>
                  <p className="mt-1 text-slate-900">{user?.name}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700">登录方式</label>
                  <p className="mt-1 text-slate-900">{user?.provider}</p>
                </div>
              </div>
            </div>
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}
