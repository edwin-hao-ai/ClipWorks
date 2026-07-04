'use client';

import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { AuthGuard } from '@/components/layout/AuthGuard';

export default function BillingPage() {
  return (
    <AuthGuard>
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="flex-1 flex flex-col">
          <TopBar title="计费" />
          <main className="flex-1 p-8">
            <div className="max-w-2xl bg-white rounded-xl border border-slate-200 p-6">
              <h2 className="text-lg font-semibold text-slate-900 mb-4">用量统计</h2>
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="bg-slate-50 rounded-lg p-4 text-center">
                  <p className="text-2xl font-bold text-slate-900">12</p>
                  <p className="text-xs text-slate-500">已生成视频</p>
                </div>
                <div className="bg-slate-50 rounded-lg p-4 text-center">
                  <p className="text-2xl font-bold text-slate-900">3</p>
                  <p className="text-xs text-slate-500">剩余次数</p>
                </div>
                <div className="bg-slate-50 rounded-lg p-4 text-center">
                  <p className="text-2xl font-bold text-slate-900">0</p>
                  <p className="text-xs text-slate-500">当前套餐</p>
                </div>
              </div>
              <p className="text-sm text-slate-500">计费系统将在后续版本接入。</p>
            </div>
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}
