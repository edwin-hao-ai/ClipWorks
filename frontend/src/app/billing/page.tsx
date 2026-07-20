'use client';

import { useEffect, useState } from 'react';
import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { AuthGuard } from '@/components/layout/AuthGuard';
import { Film, Zap, CreditCard, Check } from 'lucide-react';
import { api } from '@/lib/api';

interface UsageStats {
  videos_generated: number;
  remaining_credits: number;
  current_plan: string;
}

type PlanKey = 'free' | 'pro' | 'enterprise';

const PLAN_META: Record<PlanKey, { label: string; price: string; credits: string; features: string[] }> = {
  free: { label: '免费版', price: '¥0', credits: '10 次/月', features: ['基础时间线编辑', '720p 导出', '社区素材'] },
  pro: { label: '专业版', price: '¥29/月', credits: '200 次/月', features: ['无限时长', '1080p 导出', '优先渲染队列', '品牌模板'] },
  enterprise: { label: '企业版', price: '联系我们', credits: '不限', features: ['4K 导出', '专属渲染集群', '团队协作', 'API 访问'] },
};
const PLAN_ORDER: PlanKey[] = ['free', 'pro', 'enterprise'];

export default function BillingPage() {
  const [stats, setStats] = useState<UsageStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [updating, setUpdating] = useState<PlanKey | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    api
      .get('/auth/me/stats')
      .then((data) => {
        if (!cancelled) setStats(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : '加载用量失败');
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const currentPlan = (stats?.current_plan || 'free') as PlanKey;

  const switchPlan = async (plan: PlanKey) => {
    if (plan === currentPlan || updating) return;
    setUpdating(plan);
    setError(null);
    try {
      await api.put('/auth/me', { plan });
      const fresh = await api.get('/auth/me/stats');
      setStats(fresh);
      // 通知 TopBar 额度徽章刷新（切换套餐会按新套餐补足额度）。
      window.dispatchEvent(new CustomEvent('cw:stats-changed'));
    } catch (err) {
      setError(err instanceof Error ? err.message : '切换套餐失败');
    } finally {
      setUpdating(null);
    }
  };

  const planLabel: Record<string, string> = {
    free: '免费版',
    pro: '专业版',
    enterprise: '企业版',
  };

  return (
    <AuthGuard>
      <div className="flex min-h-screen bg-background-base">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <TopBar title="计费" />
          <main id="cw-main" className="flex-1 p-6 overflow-auto">
            <div className="max-w-3xl">
              <h2 className="text-2xl font-bold text-content-primary mb-2">用量统计</h2>
              <p className="text-sm text-content-secondary mb-6">查看你的生成用量和套餐信息</p>

              {error && (
                <div className="mb-4 text-sm text-error bg-error/10 border border-error/20 rounded-md px-4 py-3">
                  {error}
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
                <div className="bg-background-surface border border-border-subtle rounded-md p-5 text-center hover:border-border-default transition-colors">
                  <div className="w-10 h-10 mx-auto mb-3 rounded-full bg-brand-900/40 flex items-center justify-center text-brand-400">
                    <Film className="w-5 h-5" />
                  </div>
                  <p data-testid="stat-videos" className="text-3xl font-bold text-content-primary mb-1">
                    {loading ? '-' : stats?.videos_generated ?? 0}
                  </p>
                  <p className="text-xs text-content-secondary">已生成视频</p>
                </div>
                <div className="bg-background-surface border border-border-subtle rounded-md p-5 text-center hover:border-border-default transition-colors">
                  <div className="w-10 h-10 mx-auto mb-3 rounded-full bg-success/10 flex items-center justify-center text-success">
                    <Zap className="w-5 h-5" />
                  </div>
                  <p data-testid="stat-credits" className="text-3xl font-bold text-content-primary mb-1">
                    {loading ? '-' : stats?.remaining_credits ?? 0}
                  </p>
                  <p className="text-xs text-content-secondary">剩余次数</p>
                </div>
                <div className="bg-background-surface border border-border-subtle rounded-md p-5 text-center hover:border-border-default transition-colors">
                  <div className="w-10 h-10 mx-auto mb-3 rounded-full bg-background-elevated flex items-center justify-center text-content-secondary">
                    <CreditCard className="w-5 h-5" />
                  </div>
                  <p data-testid="stat-plan" className="text-3xl font-bold text-content-primary mb-1">
                    {loading ? '-' : planLabel[stats?.current_plan || 'free'] || stats?.current_plan}
                  </p>
                  <p className="text-xs text-content-secondary">当前套餐</p>
                </div>
              </div>

              <div className="bg-background-surface border border-border-subtle rounded-md p-6">
                <h3 className="text-lg font-semibold text-content-primary mb-3">计费说明</h3>
                <p className="text-sm text-content-secondary leading-relaxed">
                  每次成功渲染成片会消耗 1 次生成额度。当前为{loading ? '…' : PLAN_META[currentPlan]?.label || '免费版'}，
                  额度用完后可升级套餐继续使用。
                </p>
              </div>

              <h3 className="text-lg font-semibold text-content-primary mt-8 mb-3">选择套餐</h3>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {PLAN_ORDER.map((key) => {
                  const meta = PLAN_META[key];
                  const isCurrent = currentPlan === key;
                  const isBusy = updating === key;
                  return (
                    <div
                      key={key}
                      data-testid={`plan-card-${key}`}
                      className={`relative bg-background-surface border rounded-md p-5 flex flex-col transition-colors ${
                        isCurrent ? 'border-brand-500 ring-1 ring-brand-500/40' : 'border-border-subtle hover:border-border-default'
                      }`}
                    >
                      {isCurrent && (
                        <span className="absolute top-3 right-3 text-[11px] px-2 py-0.5 rounded-full bg-brand-600 text-white">
                          当前
                        </span>
                      )}
                      <p className="text-base font-semibold text-content-primary">{meta.label}</p>
                      <p className="text-2xl font-bold text-content-primary mt-1">{meta.price}</p>
                      <p className="text-xs text-brand-400 mt-1">{meta.credits}</p>
                      <ul className="mt-4 space-y-1.5 flex-1">
                        {meta.features.map((f) => (
                          <li key={f} className="text-xs text-content-secondary flex items-center gap-1.5">
                            <Check className="w-3.5 h-3.5 text-success shrink-0" /> {f}
                          </li>
                        ))}
                      </ul>
                      <button
                        type="button"
                        data-testid={`plan-select-${key}`}
                        disabled={isCurrent || !!updating || loading}
                        onClick={() => switchPlan(key)}
                        className={`mt-4 w-full inline-flex items-center justify-center gap-1.5 px-3 py-2 rounded-md text-sm font-medium transition-colors disabled:opacity-60 ${
                          isCurrent
                            ? 'bg-background-elevated text-content-tertiary cursor-default'
                            : 'bg-brand-600 hover:bg-brand-500 text-white'
                        }`}
                      >
                        {isCurrent ? '当前使用中' : isBusy ? '切换中…' : '切换到此套餐'}
                      </button>
                    </div>
                  );
                })}
              </div>
              <p className="mt-3 text-xs text-content-tertiary">
                演示环境：套餐切换为本地 mock，不产生真实支付。
              </p>
            </div>
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}
