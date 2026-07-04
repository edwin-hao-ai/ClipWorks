'use client';

import { useAuthStore } from '@/stores/authStore';

export function TopBar({ title }: { title?: string }) {
  const user = useAuthStore((s) => s.user);

  return (
    <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6">
      <h1 className="text-lg font-semibold text-slate-900">{title}</h1>
      <div className="flex items-center gap-3">
        {user?.avatar_url && (
          <img src={user.avatar_url} alt={user.name} className="w-8 h-8 rounded-full" />
        )}
        <span className="text-sm text-slate-700">{user?.name || user?.email}</span>
      </div>
    </header>
  );
}
