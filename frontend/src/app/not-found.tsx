import Link from 'next/link';
import { Film } from 'lucide-react';

export default function NotFound() {
  return (
    <main
      id="cw-main"
      className="min-h-dvh bg-background-base flex flex-col items-center justify-center px-6 text-center"
    >
      <div className="w-12 h-12 bg-brand-600 rounded-md flex items-center justify-center shadow-glow mb-6">
        <Film className="w-7 h-7 text-content-inverse" />
      </div>
      <p className="text-6xl font-bold text-content-primary tracking-tight">404</p>
      <h1 className="mt-3 text-lg font-semibold text-content-primary">这个页面不存在</h1>
      <p className="mt-2 text-sm text-content-secondary max-w-sm">
        链接可能已经失效，或者项目已被删除。
      </p>
      <div className="mt-8 flex items-center gap-3">
        <Link
          href="/"
          className="px-5 py-2.5 rounded-md bg-brand-600 hover:bg-brand-700 text-content-inverse text-sm font-medium transition-colors duration-150"
        >
          回到首页
        </Link>
        <Link
          href="/projects"
          className="px-5 py-2.5 rounded-md border border-border-default text-content-secondary hover:text-content-primary hover:bg-background-hover text-sm font-medium transition-colors duration-150"
        >
          查看项目库
        </Link>
      </div>
    </main>
  );
}
