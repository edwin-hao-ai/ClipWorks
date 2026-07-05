'use client';

import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';

interface TopBarProps {
  title?: string;
  showBack?: boolean;
  backHref?: string;
  right?: React.ReactNode;
}

export function TopBar({ title, showBack = false, backHref = '/projects', right }: TopBarProps) {
  return (
    <header className="h-14 border-b border-border-subtle bg-background-surface/80 backdrop-blur flex items-center justify-between px-4 shrink-0">
      <div className="flex items-center gap-3 min-w-0">
        {showBack && (
          <Link href={backHref} className="text-text-secondary hover:text-content-primary transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
        )}
        {title && <h1 className="text-sm font-semibold text-content-primary truncate">{title}</h1>}
      </div>
      {right && <div className="flex items-center gap-2 shrink-0">{right}</div>}
    </header>
  );
}
