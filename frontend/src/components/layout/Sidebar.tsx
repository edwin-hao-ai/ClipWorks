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
    <aside className="w-64 h-screen bg-white border-r border-slate-200 flex flex-col">
      <div className="p-6 flex items-center gap-3">
        <div className="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center">
          <Film className="w-5 h-5 text-white" />
        </div>
        <span className="font-bold text-lg text-slate-900">ClipWorks</span>
      </div>
      <nav className="flex-1 px-4 space-y-1">
        {nav.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={clsx(
              'flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium',
              pathname.startsWith(item.href)
                ? 'bg-brand-50 text-brand-700'
                : 'text-slate-600 hover:bg-slate-50'
            )}
          >
            <item.icon className="w-5 h-5" />
            {item.label}
          </Link>
        ))}
      </nav>
      <div className="p-4 border-t border-slate-200">
        <button
          onClick={logout}
          className="flex items-center gap-3 px-4 py-2.5 w-full rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-50"
        >
          <LogOut className="w-5 h-5" />
          退出登录
        </button>
      </div>
    </aside>
  );
}
