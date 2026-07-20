'use client';

import { useEffect } from 'react';
import { AlertTriangle } from 'lucide-react';

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // 客户端运行时错误统一上报到控制台，便于排查（生产可接监控）。
    console.error(error);
  }, [error]);

  return (
    <main
      id="cw-main"
      className="min-h-dvh bg-background-base flex flex-col items-center justify-center px-6 text-center"
    >
      <div className="w-12 h-12 bg-error/15 rounded-md flex items-center justify-center mb-6">
        <AlertTriangle className="w-7 h-7 text-error" />
      </div>
      <h1 className="text-lg font-semibold text-content-primary">页面出错了</h1>
      <p className="mt-2 text-sm text-content-secondary max-w-sm">
        渲染时遇到意外错误。你可以重试，或者回到首页重新开始。
      </p>
      <div className="mt-8 flex items-center gap-3">
        <button
          type="button"
          onClick={reset}
          className="px-5 py-2.5 rounded-md bg-brand-600 hover:bg-brand-700 text-content-inverse text-sm font-medium transition-colors duration-150"
        >
          重试
        </button>
        <a
          href="/"
          className="px-5 py-2.5 rounded-md border border-border-default text-content-secondary hover:text-content-primary hover:bg-background-hover text-sm font-medium transition-colors duration-150"
        >
          回到首页
        </a>
      </div>
    </main>
  );
}
