'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Film, LogOut } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import { clsx } from 'clsx';

// 全局素材库页面尚未实现，不在导航放伪链接（原「素材库」指向项目库，已移除）。
const links = [
  { href: '/', label: '创作' },
  { href: '/projects', label: '项目库' },
  { href: '/settings', label: '设置' },
];

export function LaunchNav() {
  const logout = useAuthStore((s) => s.logout);
  const pathname = usePathname();

  return (
    <nav className="h-16 px-4 sm:px-6 flex items-center justify-between gap-4 bg-background-surface/80 backdrop-blur border-b border-border-subtle">
      <Link href="/" className="focus-ring flex items-center gap-2 shrink-0">
        <div className="w-8 h-8 bg-brand-600 rounded-md flex items-center justify-center shadow-glow">
          <Film className="w-5 h-5 text-content-inverse" />
        </div>
        <span className="font-bold text-content-primary whitespace-nowrap">ClipWorks</span>
      </Link>
      <div className="flex items-center gap-3 sm:gap-6 text-sm text-content-secondary shrink-0">
        {links.map((l) => {
          const active = l.href === '/' ? pathname === '/' : pathname.startsWith(l.href);
          return (
            <Link
              key={l.href}
              href={l.href}
              aria-current={active ? 'page' : undefined}
              className={clsx(
                'focus-ring whitespace-nowrap transition-colors',
                active ? 'text-content-primary' : 'hover:text-content-primary'
              )}
            >
              {l.label}
            </Link>
          );
        })}
        <button
          type="button"
          onClick={logout}
          aria-label="退出登录"
          title="退出登录"
          className="focus-ring w-8 h-8 rounded-full bg-background-elevated border border-border-default flex items-center justify-center text-content-secondary hover:text-content-primary transition-colors shrink-0"
        >
          <LogOut className="w-4 h-4" />
        </button>
      </div>
    </nav>
  );
}
