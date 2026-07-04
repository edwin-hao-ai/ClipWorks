'use client';

import { Film } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { useAuthStore } from '@/stores/authStore';

export default function LoginPage() {
  const login = useAuthStore((s) => s.login);

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-sm border border-slate-200 p-8">
        <div className="flex justify-center mb-6">
          <div className="w-12 h-12 bg-brand-600 rounded-xl flex items-center justify-center">
            <Film className="w-7 h-7 text-white" />
          </div>
        </div>
        <h1 className="text-2xl font-bold text-center text-slate-900 mb-2">ClipWorks 映工厂</h1>
        <p className="text-center text-slate-500 mb-8">AI 驱动的视频生成与剪辑工具</p>
        <div className="space-y-3">
          <Button size="lg" className="w-full" onClick={() => login('google')}>
            使用 Google 登录
          </Button>
          <Button size="lg" variant="secondary" className="w-full" onClick={() => login('github')}>
            使用 GitHub 登录
          </Button>
        </div>
      </div>
    </div>
  );
}
