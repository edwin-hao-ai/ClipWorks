'use client';

import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { AuthGuard } from '@/components/layout/AuthGuard';
import { Film, Zap, CreditCard } from 'lucide-react';

export default function BillingPage() {
  return (
    <AuthGuard>
      <div className="flex min-h-screen bg-background-base">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <TopBar title="计费" />
          <main className="flex-1 p-6 overflow-auto">
            <div className="max-w-3xl">
              <h2 className="text-2xl font-bold text-content-primary mb-2">用量统计</h2>
              <p className="text-sm text-content-secondary mb-6">查看你的生成用量和套餐信息</p>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
                <div className="bg-background-surface border border-border-subtle rounded-md p-5 text-center hover:border-border-default transition-colors">
                  <div className="w-10 h-10 mx-auto mb-3 rounded-full bg-brand-900/40 flex items-center justify-center text-brand-400">
                    <Film className="w-5 h-5" />
                  </div>
                  <p className="text-3xl font-bold text-content-primary mb-1">12</p>
                  <p className="text-xs text-content-secondary">已生成视频</p>
                </div>
                <div className="bg-background-surface border border-border-subtle rounded-md p-5 text-center hover:border-border-default transition-colors">
                  <div className="w-10 h-10 mx-auto mb-3 rounded-full bg-success/10 flex items-center justify-center text-success">
                    <Zap className="w-5 h-5" />
                  </div>
                  <p className="text-3xl font-bold text-content-primary mb-1">3</p>
                  <p className="text-xs text-content-secondary">剩余次数</p>
                </div>
                <div className="bg-background-surface border border-border-subtle rounded-md p-5 text-center hover:border-border-default transition-colors">
                  <div className="w-10 h-10 mx-auto mb-3 rounded-full bg-background-elevated flex items-center justify-center text-content-secondary">
                    <CreditCard className="w-5 h-5" />
                  </div>
                  <p className="text-3xl font-bold text-content-primary mb-1">0</p>
                  <p className="text-xs text-content-secondary">当前套餐</p>
                </div>
              </div>

              <div className="bg-background-surface border border-border-subtle rounded-md p-6">
                <h3 className="text-lg font-semibold text-content-primary mb-3">计费说明</h3>
                <p className="text-sm text-content-secondary leading-relaxed">
                  计费系统将在后续版本接入。当前为原型演示阶段，所有生成和下载均为模拟数据，不消耗真实额度。
                </p>
              </div>
            </div>
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}
