'use client';

import Link from 'next/link';
import { Film } from 'lucide-react';

export function LaunchNav() {
  return (
    <nav className="h-16 px-6 flex items-center justify-between bg-background-surface/80 backdrop-blur border-b border-border-subtle">
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 bg-brand-600 rounded-md flex items-center justify-center shadow-glow">
          <Film className="w-5 h-5 text-content-inverse" />
        </div>
        <span className="font-bold text-content-primary">ClipWorks</span>
      </div>
      <div className="flex items-center gap-6 text-sm text-content-secondary">
        <Link href="/" className="text-content-primary hover:text-brand-400 transition-colors">创作</Link>
        <Link href="/projects" className="hover:text-content-primary transition-colors">项目库</Link>
        <Link href="/projects/demo/assets" className="hover:text-content-primary transition-colors">素材库</Link>
        <Link href="/settings" className="hover:text-content-primary transition-colors">设置</Link>
        <div className="w-8 h-8 rounded-full bg-background-elevated border border-border-default" />
      </div>
    </nav>
  );
}
