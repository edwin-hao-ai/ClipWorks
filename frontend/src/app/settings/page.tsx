'use client';

import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { AuthGuard } from '@/components/layout/AuthGuard';
import { useAuthStore } from '@/stores/authStore';
import { Mail, User, Shield, Bell } from 'lucide-react';

export default function SettingsPage() {
  const user = useAuthStore((s) => s.user);

  const items = [
    { icon: User, label: '昵称', value: user?.name || '-' },
    { icon: Mail, label: '邮箱', value: user?.email || '-' },
    { icon: Shield, label: '登录方式', value: user?.provider || '-' },
    { icon: Bell, label: '通知', value: '邮件通知已开启' },
  ];

  return (
    <AuthGuard>
      <div className="flex min-h-screen bg-background-base">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <TopBar title="设置" />
          <main className="flex-1 p-6 overflow-auto">
            <div className="max-w-2xl">
              <h2 className="text-2xl font-bold text-content-primary mb-2">账户设置</h2>
              <p className="text-sm text-content-secondary mb-6">管理你的账户信息和偏好</p>
              <div className="bg-background-surface border border-border-subtle rounded-md p-6">
                <h3 className="text-lg font-semibold text-content-primary mb-5">账户信息</h3>
                <div className="space-y-4">
                  {items.map((item) => (
                    <div
                      key={item.label}
                      className="flex items-center justify-between py-3 border-b border-border-subtle last:border-0 last:pb-0"
                    >
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-md bg-background-elevated flex items-center justify-center text-content-secondary">
                          <item.icon className="w-4 h-4" />
                        </div>
                        <span className="text-sm text-content-secondary">{item.label}</span>
                      </div>
                      <span className="text-sm font-medium text-content-primary">{item.value}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}
