'use client';

import { useEffect, useRef, useState } from 'react';
import Link from 'next/link';
import { ArrowLeft, LogOut, Zap } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import { api } from '@/lib/api';

interface TopBarProps {
  title?: string;
  showBack?: boolean;
  backHref?: string;
  right?: React.ReactNode;
}

export function TopBar({ title, showBack = false, backHref = '/projects', right }: TopBarProps) {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const [menuOpen, setMenuOpen] = useState(false);
  const [credits, setCredits] = useState<number | null>(null);
  const menuRef = useRef<HTMLDivElement>(null);

  // 下拉菜单打开后：Esc 或点击菜单外部区域均可关闭。否则菜单会一直挂在
  // z-50 层上，遮住其下方的页面按钮（实测编辑器「保存」按钮会被挡住点不动）。
  useEffect(() => {
    if (!menuOpen) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMenuOpen(false);
    };
    const onMouseDown = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener('keydown', onKeyDown);
    document.addEventListener('mousedown', onMouseDown);
    return () => {
      document.removeEventListener('keydown', onKeyDown);
      document.removeEventListener('mousedown', onMouseDown);
    };
  }, [menuOpen]);

  useEffect(() => {
    let cancelled = false;
    const fetchStats = () => {
      api
        .get('/auth/me/stats')
        .then((data) => {
          if (!cancelled && typeof data?.remaining_credits === 'number') {
            setCredits(data.remaining_credits);
          }
        })
        .catch(() => {});
    };
    fetchStats();
    // 渲染扣费、套餐切换发生在其他页面/组件：窗口重新聚焦或收到
    // cw:stats-changed 事件时刷新徽章，避免长期显示旧额度。
    window.addEventListener('focus', fetchStats);
    window.addEventListener('cw:stats-changed', fetchStats);
    return () => {
      cancelled = true;
      window.removeEventListener('focus', fetchStats);
      window.removeEventListener('cw:stats-changed', fetchStats);
    };
  }, []);

  return (
    <header className="h-14 border-b border-border-subtle bg-background-surface/80 backdrop-blur flex items-center justify-between px-4 shrink-0">
      <div className="flex items-center gap-3 min-w-0">
        {showBack && (
          <Link href={backHref} className="focus-ring text-content-secondary hover:text-content-primary transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
        )}
        {title && <h1 className="text-sm font-semibold text-content-primary truncate">{title}</h1>}
      </div>
      {right ? (
        <div className="flex items-center gap-2 shrink-0">{right}</div>
      ) : (
        <div ref={menuRef} className="relative flex items-center gap-3 shrink-0">
          {credits !== null && (
            <Link
              href="/billing"
              data-testid="credits-badge"
              title="剩余生成次数，点击查看计费"
              className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium transition-colors ${
                credits === 0
                  ? 'bg-error/15 text-error hover:bg-error/25'
                  : credits <= 2
                  ? 'bg-warning/15 text-warning hover:bg-warning/25'
                  : 'bg-brand-900/40 text-brand-300 hover:bg-brand-900/60'
              }`}
            >
              <Zap className="w-3.5 h-3.5" />
              <span data-testid="credits-value">{credits}</span>
              <span className="hidden sm:inline">次</span>
            </Link>
          )}
          <div className="text-right hidden sm:block">
            <p className="text-sm font-medium text-content-primary leading-tight">{user?.name || user?.email}</p>
            {user?.name && user?.email && (
              <p className="text-xs text-content-tertiary leading-tight">{user.email}</p>
            )}
          </div>
          <button
            type="button"
            onClick={() => setMenuOpen((o) => !o)}
            aria-label="账户菜单"
            aria-expanded={menuOpen}
            className="rounded-full focus:outline-none focus:ring-2 focus:ring-brand-500/60"
          >
            {user?.avatar_url ? (
              <img
                src={user.avatar_url}
                alt={user.name || user.email}
                className="w-8 h-8 rounded-full border border-border-default bg-background-elevated"
              />
            ) : (
              <div className="w-8 h-8 rounded-full bg-brand-600 flex items-center justify-center text-content-inverse text-sm font-semibold">
                {user?.name?.[0] || user?.email?.[0] || '?'}
              </div>
            )}
          </button>
          {menuOpen && (
            <div className="absolute right-0 top-full mt-2 w-56 rounded-lg border border-border-subtle bg-background-surface shadow-lg z-50 overflow-hidden">
              <div className="px-3 py-2 text-xs text-content-tertiary truncate border-b border-border-subtle">
                {user?.email || '未登录'}
              </div>
              <button
                type="button"
                onClick={logout}
                className="focus-ring flex items-center gap-2 w-full px-3 py-2 text-sm text-content-secondary hover:bg-background-hover hover:text-content-primary transition-colors"
              >
                <LogOut className="w-4 h-4" />
                退出登录
              </button>
            </div>
          )}
        </div>
      )}
    </header>
  );
}
