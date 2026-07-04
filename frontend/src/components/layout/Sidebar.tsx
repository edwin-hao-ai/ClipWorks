'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Film, FolderOpen, Settings, CreditCard, LogOut } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import { clsx } from 'clsx';

const nav = [
  { href: '/projects', label: '项目', icon: FolderOpen },
  { href: '/settings', label: '设置', icon: Settings },
  { href: '/billing', label: '计费', icon: CreditCard },
];

export function Sidebar() {
  const pathname = usePathname();
  const logout = useAuthStore((s) => s.logout);

  return (
    <aside className="w-60 h-screen bg-background-surface border-r border-border-subtle flex flex-col shrink-0">
      <div className="h-14 px-5 flex items-center gap-3 border-b border-border-subtle">
        <div className="w-8 h-8 bg-brand-600 rounded-md flex items-center justify-center shadow-glow">
          <Film className="w-5 h-5 text-content-inverse" />
        </div>
        <span className="font-bold text-base text-content-primary">ClipWorks</span>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-1">
        {nav.map((item) => {
          const active = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                'flex items-center gap-3 px-4 py-2.5 rounded-md text-sm font-medium transition-colors duration-150',
                active
                  ? 'bg-brand-900/60 text-brand-400 border-l-[3px] border-brand-500'
                  : 'text-content-secondary hover:bg-background-hover hover:text-content-primary'
              )}
            >
              <item.icon className="w-5 h-5" />
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="p-3 border-t border-border-subtle">
        <button
          onClick={logout}
          className="flex items-center gap-3 px-4 py-2.5 w-full rounded-md text-sm font-medium text-content-secondary hover:bg-background-hover hover:text-content-primary transition-colors duration-150"
        >
          <LogOut className="w-5 h-5" />
          退出登录
        </button>
      </div>
    </aside>
  );
}
