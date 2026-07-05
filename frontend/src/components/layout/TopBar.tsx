'use client';

import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';

interface TopBarProps {
  title?: string;
  showBack?: boolean;
  backHref?: string;
  right?: React.ReactNode;
}

export function TopBar({ title, showBack = false, backHref = '/projects', right }: TopBarProps) {
  const user = useAuthStore((s) => s.user);

  return (
    <header className="h-14 border-b border-border-subtle bg-background-surface/80 backdrop-blur flex items-center justify-between px-4 shrink-0">
      <div className="flex items-center gap-3 min-w-0">
        {showBack && (
          <Link href={backHref} className="text-content-secondary hover:text-content-primary transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
        )}
        {title && <h1 className="text-sm font-semibold text-content-primary truncate">{title}</h1>}
      </div>
      {right ? (
        <div className="flex items-center gap-2 shrink-0">{right}</div>
      ) : (
        <div className="flex items-center gap-3 shrink-0">
          <div className="text-right hidden sm:block">
            <p className="text-sm font-medium text-content-primary leading-tight">{user?.name || user?.email}</p>
            {user?.name && user?.email && (
              <p className="text-xs text-content-tertiary leading-tight">{user.email}</p>
            )}
          </div>
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
        </div>
      )}
    </header>
  );
}
