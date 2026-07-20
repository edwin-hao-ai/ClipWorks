'use client';

import Link from 'next/link';
import { Film, Github } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { useAuthStore } from '@/stores/authStore';

export default function LoginPage() {
  const login = useAuthStore((s) => s.login);
  const loginLoading = useAuthStore((s) => s.loginLoading);
  const loginError = useAuthStore((s) => s.loginError);

  return (
    <main id="cw-main" className="relative min-h-dvh flex items-center justify-center bg-background-base overflow-hidden">
      {/* Gradient glow */}
      <div
        className="absolute -top-1/4 -left-1/4 w-[60vw] h-[60vw] rounded-full opacity-20 pointer-events-none"
        style={{
          background: 'radial-gradient(circle, var(--brand-900) 0%, transparent 70%)',
        }}
      />

      {/* Subtle grid */}
      <div
        className="absolute inset-0 pointer-events-none opacity-[0.05]"
        style={{
          backgroundImage:
            'linear-gradient(var(--border-default) 1px, transparent 1px), linear-gradient(90deg, var(--border-default) 1px, transparent 1px)',
          backgroundSize: '40px 40px',
        }}
      />

      <div className="relative w-full max-w-md px-6">
        <div className="bg-background-surface/80 backdrop-blur-xl border border-border-default rounded-lg shadow-lg p-8">
          <div className="flex justify-center mb-6">
            <div className="w-14 h-14 bg-brand-600 rounded-xl flex items-center justify-center shadow-glow">
              <Film className="w-8 h-8 text-content-inverse" />
            </div>
          </div>
          <h1 className="text-3xl font-bold text-center text-content-primary mb-2">ClipWorks 映工厂</h1>
          <p className="text-center text-content-secondary mb-8">AI 驱动的视频生成与剪辑工具</p>
          <p className="text-center text-content-tertiary text-sm mb-8">
            一句话，一段素材，一条成片。
          </p>
          {loginError && (
            <div className="mb-4 text-sm text-error bg-error/10 border border-error/20 rounded-md px-4 py-2">
              {loginError.includes('NetworkError') || loginError.includes('fetch')
                ? '无法连接到登录服务，请确认后端服务已启动。'
                : loginError}
            </div>
          )}
          <div className="space-y-3">
            <Button
              size="lg"
              className="w-full animate-pulseGlow"
              onClick={() => login('google')}
              disabled={loginLoading}
            >
              {loginLoading ? (
                <span className="w-5 h-5 mr-2 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <svg className="w-5 h-5 mr-2" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" />
                  <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" />
                  <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" />
                  <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" />
                </svg>
              )}
              {loginLoading ? '登录中…' : '使用 Google 登录'}
            </Button>
            <Button
              size="lg"
              variant="secondary"
              className="w-full"
              onClick={() => login('github')}
              disabled={loginLoading}
            >
              <Github className="w-5 h-5 mr-2" />
              使用 GitHub 登录
            </Button>
          </div>
          <p className="mt-6 text-center text-xs text-content-tertiary leading-relaxed">
            登录即表示你已阅读并同意
            <Link
              href="/terms"
              className="text-content-secondary hover:text-brand-400 underline-offset-2 hover:underline mx-1 transition-colors whitespace-nowrap"
            >
              《服务条款》
            </Link>
            与
            <Link
              href="/privacy"
              className="text-content-secondary hover:text-brand-400 underline-offset-2 hover:underline mx-1 transition-colors whitespace-nowrap"
            >
              《隐私政策》
            </Link>
            <span className="whitespace-nowrap">（草案）</span>
          </p>
          <p className="mt-4 text-center text-xs text-content-tertiary">
            ClipWorks 映工厂 · AI 视频工厂
          </p>
        </div>
      </div>
    </main>
  );
}
