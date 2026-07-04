'use client';

import { useAuthStore } from '@/stores/authStore';

export function TopBar({ title }: { title?: string }) {
  const user = useAuthStore((s) => s.user);

  return (
    <header className="h-14 bg-background-surface/80 backdrop-blur border-b border-border-subtle flex items-center justify-between px-6 shrink-0 sticky top-0 z-20">
      <h1 className="text-base font-semibold text-content-primary">{title}</h1>
      <div className="flex items-center gap-3">
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
    </header>
  );
}
