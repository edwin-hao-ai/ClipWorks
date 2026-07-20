'use client';

import { useEffect, useState } from 'react';
import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { AuthGuard } from '@/components/layout/AuthGuard';
import { useAuthStore } from '@/stores/authStore';
import { api } from '@/lib/api';
import { Mail, User, Shield, Bell, Palette, Pencil, Check, X, Save } from 'lucide-react';

type Theme = 'dark' | 'light';

export default function SettingsPage() {
  const user = useAuthStore((s) => s.user);
  const fetchMe = useAuthStore((s) => s.fetchMe);

  const [editing, setEditing] = useState(false);
  const [nameInput, setNameInput] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle');

  // 偏好（本地持久化）：通知开关与主题。默认开启通知、深色主题，保持与既有 UI 一致。
  const [notif, setNotif] = useState(true);
  const [theme, setTheme] = useState<Theme>('dark');

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const n = window.localStorage.getItem('cw_notifications');
    if (n !== null) setNotif(n === '1');
    const t = window.localStorage.getItem('cw_theme') as Theme | null;
    if (t === 'light' || t === 'dark') setTheme(t);
  }, []);

  useEffect(() => {
    if (typeof document === 'undefined') return;
    if (theme === 'light') document.documentElement.dataset.theme = 'light';
    else delete document.documentElement.dataset.theme;
  }, [theme]);

  const toggleNotif = () => {
    const next = !notif;
    setNotif(next);
    if (typeof window !== 'undefined') window.localStorage.setItem('cw_notifications', next ? '1' : '0');
  };

  const toggleTheme = () => {
    const next: Theme = theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
    if (typeof window !== 'undefined') window.localStorage.setItem('cw_theme', next);
  };

  const saveName = async () => {
    const name = nameInput.trim();
    if (!name || saving) return;
    setSaving(true);
    setSaveStatus('idle');
    try {
      await api.put('/auth/me', { name });
      await fetchMe();
      setEditing(false);
      setSaveStatus('success');
      setTimeout(() => setSaveStatus('idle'), 2500);
    } catch {
      setSaveStatus('error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <AuthGuard>
      <div className="flex min-h-dvh bg-background-base">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <TopBar title="设置" />
          <main id="cw-main" className="flex-1 p-6 overflow-auto">
            <div className="max-w-2xl">
              <h2 className="text-2xl font-bold text-content-primary mb-2">账户设置</h2>
              <p className="text-sm text-content-secondary mb-6">管理你的账户信息和偏好</p>
              <div className="bg-background-surface border border-border-subtle rounded-md p-6">
                <h3 className="text-lg font-semibold text-content-primary mb-5">账户信息</h3>
                <div className="space-y-1">
                  {/* 昵称：默认展示，点击编辑切换为输入框 + 保存 */}
                  <Row icon={User} label="昵称">
                    {editing ? (
                      <div className="flex items-center gap-2">
                        <input
                          value={nameInput}
                          onChange={(e) => setNameInput(e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') saveName();
                            if (e.key === 'Escape') setEditing(false);
                          }}
                          maxLength={80}
                          autoFocus
                          className="bg-background-base border border-border-default rounded-md px-2 py-1 text-sm text-content-primary outline-none focus:border-brand-500 w-44"
                        />
                        <button
                          onClick={saveName}
                          disabled={saving || !nameInput.trim()}
                          aria-label="保存昵称"
                          className="p-1.5 rounded-md text-success hover:bg-success/10 disabled:opacity-40"
                        >
                          <Check className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => setEditing(false)}
                          aria-label="取消"
                          className="p-1.5 rounded-md text-content-tertiary hover:bg-background-hover"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      </div>
                    ) : (
                      <div className="flex items-center gap-2">
                        <span data-testid="setting-value-昵称" className="text-sm font-medium text-content-primary">
                          {user?.name || '-'}
                        </span>
                        <button
                          onClick={() => {
                            setNameInput(user?.name || '');
                            setEditing(true);
                          }}
                          aria-label="编辑昵称"
                          className="p-1 rounded-md text-content-tertiary hover:text-content-primary hover:bg-background-hover"
                        >
                          <Pencil className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    )}
                  </Row>

                  <Row icon={Mail} label="邮箱">
                    <span data-testid="setting-value-邮箱" className="text-sm font-medium text-content-primary">
                      {user?.email || '-'}
                    </span>
                  </Row>

                  <Row icon={Shield} label="登录方式">
                    <span data-testid="setting-value-登录方式" className="text-sm font-medium text-content-primary">
                      {user?.provider || '-'}
                    </span>
                  </Row>

                  <Row icon={Bell} label="通知">
                    <button
                      onClick={toggleNotif}
                      data-testid="setting-value-通知"
                      className="text-sm font-medium text-content-primary hover:text-brand-400 transition-colors"
                      title="当前为本地偏好，尚未接入服务端推送"
                    >
                      {notif ? '通知已开启（本地偏好）' : '通知已关闭（本地偏好）'}
                    </button>
                  </Row>

                  <Row icon={Palette} label="主题" last>
                    <button
                      onClick={toggleTheme}
                      className="text-sm font-medium text-content-primary hover:text-brand-400 transition-colors"
                      title="切换浅色 / 深色主题"
                    >
                      {theme === 'dark' ? '深色（点击切换浅色）' : '浅色（点击切换深色）'}
                    </button>
                  </Row>
                </div>

                {saveStatus === 'success' && (
                  <div className="mt-4 flex items-center gap-1.5 text-xs text-success">
                    <Save className="w-3.5 h-3.5" /> 昵称已保存
                  </div>
                )}
                {saveStatus === 'error' && (
                  <div className="mt-4 text-xs text-error">保存失败，请重试</div>
                )}
              </div>
            </div>
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}

function Row({
  icon: Icon,
  label,
  children,
  last,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  children: React.ReactNode;
  last?: boolean;
}) {
  return (
    <div
      className={`flex items-center justify-between py-3 ${
        last ? '' : 'border-b border-border-subtle'
      }`}
    >
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 rounded-md bg-background-elevated flex items-center justify-center text-content-secondary">
          <Icon className="w-4 h-4" />
        </div>
        <span className="text-sm text-content-secondary">{label}</span>
      </div>
      {children}
    </div>
  );
}
