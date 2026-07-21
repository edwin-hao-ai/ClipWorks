'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Film, FolderOpen, Settings, CreditCard, LogOut, Plus } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import { NewProjectDialog } from '@/components/project/NewProjectDialog';
import { clsx } from 'clsx';

const nav = [
  { href: '/projects', label: '项目', icon: FolderOpen },
  { href: '/settings', label: '设置', icon: Settings },
  { href: '/billing', label: '计费', icon: CreditCard },
];

export function Sidebar() {
  const pathname = usePathname();
  const { logout } = useAuthStore();

  return (
    // 窄屏退化为图标+文字标签轨（w-14）：固定 240px 侧栏在手机上会把内容区挤没。
    <aside className="w-14 lg:w-60 h-dvh bg-background-surface border-r border-border-subtle flex flex-col shrink-0">
      <div className="h-14 px-3 lg:px-5 flex items-center justify-center lg:justify-start gap-3 border-b border-border-subtle">
        <div className="w-8 h-8 shrink-0 bg-brand-600 rounded-md flex items-center justify-center shadow-glow">
          <Film className="w-5 h-5 text-content-inverse" />
        </div>
        <span className="hidden lg:inline font-bold text-base text-content-primary">ClipWorks</span>
      </div>
      <nav className="flex-1 px-2 lg:px-3 py-4 space-y-1">
        <NewProjectDialog
          trigger={(open) => (
            <button
              type="button"
              onClick={open}
              className="focus-ring flex flex-col lg:flex-row items-center justify-center lg:justify-start gap-0 lg:gap-3 px-2 lg:px-4 py-2.5 w-full rounded-md text-sm font-medium bg-brand-600 text-content-inverse hover:bg-brand-500 hover:shadow-glow transition-all duration-150"
            >
              <Plus className="w-5 h-5 shrink-0" />
              <span className="hidden lg:inline">新建项目</span>
              <span className="lg:hidden text-[10px] leading-tight mt-0.5 text-center">新建</span>
            </button>
          )}
        />
        {nav.map((item) => {
          const active = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? 'page' : undefined}
              title={item.label}
              className={clsx(
                'focus-ring flex flex-col lg:flex-row items-center justify-center lg:justify-start gap-0 lg:gap-3 px-2 lg:px-4 py-2.5 rounded-md text-sm font-medium transition-colors duration-150',
                active
                  ? 'nav-active lg:border-l-[3px] lg:border-brand-500'
                  : 'text-content-secondary hover:bg-background-hover hover:text-content-primary'
              )}
            >
              <item.icon className="w-5 h-5 shrink-0" />
              <span className="hidden lg:inline">{item.label}</span>
              <span className="lg:hidden text-[10px] leading-tight mt-0.5 text-center">
                {item.label}
              </span>
            </Link>
          );
        })}
      </nav>
      <div className="p-2 lg:p-3 border-t border-border-subtle">
        <button
          onClick={logout}
          title="退出登录"
          className="focus-ring flex flex-col lg:flex-row items-center justify-center lg:justify-start gap-0 lg:gap-3 px-2 lg:px-4 py-2.5 w-full rounded-md text-sm font-medium text-content-secondary hover:bg-background-hover hover:text-content-primary transition-colors duration-150"
        >
          <LogOut className="w-5 h-5 shrink-0" />
          <span className="hidden lg:inline">退出登录</span>
          <span className="lg:hidden text-[10px] leading-tight mt-0.5 text-center">退出登录</span>
        </button>
      </div>
    </aside>
  );
}
