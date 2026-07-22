'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { clsx } from 'clsx';
import { Pipeline } from './Pipeline';
import { Project, RenderJob } from '@/lib/types';
import { api } from '@/lib/api';
import {
  Sparkles,
  Check,
  Loader2,
  Circle,
  Clock,
  Terminal,
  AlertCircle,
  RefreshCw,
  ArrowLeft,
  X,
} from 'lucide-react';

interface GenerationPanelProps {
  project: Project;
  latestJob: RenderJob | null;
  steps: { id: string; label: string }[];
  currentStepIndex: number;
  currentDescription: string;
}

const STEP_DETAILS: Record<string, string> = {
  understand: '分析你的需求、目标受众和投放平台',
  analyze: '提取网页/素材的关键信息与视觉元素',
  script: '撰写视频脚本、钩子与分镜文案',
  scenes: '构建时间线场景、画面布局与动画节奏',
  render: '调用渲染引擎合成真实 MP4/HTML',
  output: '转码、封装并输出最终成片',
};

function formatShortTime(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  } catch {
    return '';
  }
}

export function GenerationPanel({
  project,
  latestJob,
  steps,
  currentStepIndex,
  currentDescription,
}: GenerationPanelProps) {
  const [tick, setTick] = useState(0);
  const [streamedJob, setStreamedJob] = useState<RenderJob | null>(null);
  const [retrying, setRetrying] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const logRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const id = setInterval(() => setTick((t) => t + 1), 500);
    return () => clearInterval(id);
  }, []);

  // Stream job updates via SSE when the project is still generating.
  useEffect(() => {
    const isActive =
      project.status === 'generating' ||
      latestJob?.status === 'queued' ||
      latestJob?.status === 'running';
    if (!isActive) return;

    let cancelled = false;
    const connect = async () => {
      try {
        for await (const event of api.streamGet(`/projects/${project.id}/renders/stream`)) {
          if (cancelled) break;
          if (event && typeof event === 'object') {
            setStreamedJob(event as RenderJob);
          }
        }
      } catch {
        // Fall back to the prop-driven polling if SSE fails.
      }
    };
    connect();
    return () => {
      cancelled = true;
    };
  }, [project.id, project.status, latestJob?.status]);

  const job = streamedJob || latestJob;
  const progress = job?.progress ?? 0;
  const jobStatus = job?.status ?? 'queued';
  const isQueued = jobStatus === 'queued';
  const isRunning = jobStatus === 'running';
  const isFailed = jobStatus === 'failed';
  const isStalled = jobStatus === 'stalled';
  const isWaiting = jobStatus === 'waiting';
  const isPlaceholder =
    jobStatus === 'completed' && !!job?.output_url && job.output_url.includes('/sample.mp4');
  const queuePosition = job?.queue_position ?? 0;
  const logs = useMemo(() => job?.logs || [], [job?.logs]);
  const visibleLogs = logs.slice(-12);
  const latestLog = logs.length > 0 ? logs[logs.length - 1] : null;
  const hasSteps = steps && steps.length > 0;
  // 无 steps 时，优先使用 job.progress；若未设置，尝试从最新日志解析百分比。
  const displayedProgress =
    progress > 0
      ? progress
      : (() => {
          const match = latestLog?.message?.match(/(\d+)%/);
          return match ? parseInt(match[1], 10) : 0;
        })();
  const hasWarningLog = logs.some(
    (l) => l.message.includes('⚠️') || l.message.includes('占位') || l.message.includes('失败')
  );
  const showPlaceholderBanner = isPlaceholder || hasWarningLog;

  // Keep the log view pinned to the newest line.
  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [visibleLogs.length]);

  // Rough ETA: each preceding job takes ~2.5 min on average in local dev.
  const estimatedMinutes = Math.max(1, queuePosition * 2);

  const handleRetry = async () => {
    if (retrying) return;
    setRetrying(true);
    try {
      await api.post(`/projects/${project.id}/renders/agent-generate`, {});
      // Reload so the project status / pipeline reset cleanly and a fresh SSE
      // connection is established for the new job.
      window.location.reload();
    } catch {
      setRetrying(false);
    }
  };

  const handleCancel = async () => {
    if (cancelling || !job?.id) return;
    setCancelling(true);
    try {
      await api.post(`/projects/${project.id}/renders/${job.id}/cancel`, {});
      // Reload so the workspace leaves the generating view and reflects the
      // cancelled state (the SSE stream also closes on its own).
      window.location.reload();
    } catch {
      setCancelling(false);
    }
  };

  const stalledMessage =
    job?.error_message ||
    (job?.stalled_reason === 'no_job'
      ? '生成任务未能启动（队列未响应）。'
      : '生成任务长时间没有新的进展，可能渲染引擎繁忙或卡住。');

  const isActive = isQueued || isRunning || isWaiting;

  return (
    <div className="w-full max-w-2xl bg-background-surface border border-border-subtle rounded-xl p-6 sm:p-8 shadow-lg">
      <div className="text-center mb-6">
        <div
          className={clsx(
            'inline-flex items-center justify-center w-12 h-12 rounded-full mb-4',
            isFailed
              ? 'bg-error/20 text-error'
              : isStalled
              ? 'bg-warning/20 text-warning'
              : isPlaceholder
              ? 'bg-warning/20 text-warning'
              : 'bg-brand-900/40 text-brand-400'
          )}
        >
          {isQueued || isWaiting ? (
            <Clock className="w-6 h-6 animate-pulse" />
          ) : isFailed ? (
            <AlertCircle className="w-6 h-6" />
          ) : isStalled ? (
            <AlertCircle className="w-6 h-6" />
          ) : (
            <Sparkles className="w-6 h-6 animate-pulse" />
          )}
        </div>
        <h2 className="text-lg font-semibold text-content-primary mb-1">
          {isFailed
            ? '生成失败'
            : isStalled
            ? '生成似乎没有响应'
            : isQueued || isWaiting
            ? `《${project.title || '未命名项目'}》已加入生成队列`
            : `正在生成《${project.title || '未命名项目'}》`}
        </h2>
        <p className="text-sm text-content-secondary">
          {isFailed
            ? job?.error_message || '生成过程中出现错误，请查看下方日志。'
            : isStalled
            ? stalledMessage
            : isPlaceholder
            ? '生成已完成，但输出的是占位视频（真实渲染不可用）。请检查 renderer 的 Chromium 配置。'
            : isWaiting
            ? '正在启动生成任务…'
            : isQueued
            ? queuePosition > 0
              ? `前面还有 ${queuePosition} 个任务在排队，预计约 ${estimatedMinutes} 分钟后开始。`
              : '排队中，即将开始生成…'
            : !hasSteps && latestLog
            ? latestLog.message
            : currentDescription}
        </p>
        <div className="flex flex-wrap items-center justify-center gap-2 mt-3 text-xs text-content-tertiary">
          <span className="px-2 py-1 rounded-full bg-background-elevated border border-border-subtle">
            画幅 {project.target_format || '16:9'}
          </span>
          {project.target_duration ? (
            <span className="px-2 py-1 rounded-full bg-background-elevated border border-border-subtle">
              目标 {project.target_duration}s
            </span>
          ) : null}
          {displayedProgress > 0 ? (
            <span className="px-2 py-1 rounded-full bg-background-elevated border border-border-subtle">
              总进度 {displayedProgress}%
            </span>
          ) : null}
        </div>
        {isActive && job?.id && (
          <button
            onClick={handleCancel}
            disabled={cancelling}
            className="mt-4 inline-flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-lg border border-border-subtle hover:border-error/50 hover:bg-error/10 text-content-secondary hover:text-error text-xs font-medium transition-colors disabled:opacity-60"
          >
            <X className="w-3.5 h-3.5" />
            {cancelling ? '正在取消…' : '取消生成'}
          </button>
        )}
      </div>

      {hasSteps && (
        <Pipeline
          steps={steps}
          currentStepIndex={isQueued || isWaiting || isStalled ? -1 : currentStepIndex}
          currentDescription={isQueued || isWaiting ? '排队中' : currentDescription}
        />
      )}

      <div className="mt-6">
        <div className="flex items-center gap-2 text-xs font-semibold text-content-secondary uppercase tracking-wider mb-3">
          <Terminal className="w-3.5 h-3.5" />
          Agent 执行日志
          {isActive && !isStalled && (
            <span className="ml-auto inline-flex items-center gap-1 text-brand-400 normal-case">
              <span className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-pulse" />
              实时更新中
            </span>
          )}
        </div>

        {showPlaceholderBanner && (
          <div className="mb-3 flex items-start gap-2 px-3 py-2 rounded-md bg-warning/10 border border-warning/30 text-xs text-warning">
            <AlertCircle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
            <span>
              输出为占位视频（sample.mp4）：真实渲染引擎在当前环境不可用，日志中的 ⚠️ 行有详细原因。
            </span>
          </div>
        )}

        <div
          ref={logRef}
          className="bg-black/40 border border-border-subtle rounded-lg p-3 font-mono text-xs h-48 overflow-y-auto space-y-1.5 mb-4 scroll-smooth"
        >
          {visibleLogs.length === 0 && (
            <div className="text-content-tertiary italic">
              {isStalled ? '没有可用的执行日志。' : '等待任务开始…'}
            </div>
          )}
          {visibleLogs.map((log, idx) => {
            const isLast = idx === visibleLogs.length - 1;
            const isWarn = log.message.includes('⚠️') || log.message.includes('失败');
            return (
              <div
                key={`${log.time}-${idx}`}
                className={clsx(
                  'flex gap-2 break-words',
                  isWarn
                    ? 'text-warning'
                    : isLast && isActive
                    ? 'text-brand-300'
                    : 'text-content-secondary'
                )}
              >
                <span className="shrink-0 text-content-tertiary">[{formatShortTime(log.time)}]</span>
                <span className="flex-1">{log.message}</span>
                {isLast && isActive && !isStalled && (
                  <span className="shrink-0 text-brand-400">▌</span>
                )}
              </div>
            );
          })}
        </div>

        {(isStalled || isFailed) && (
          <div className="mb-4 flex flex-col sm:flex-row gap-2">
            <button
              onClick={handleRetry}
              disabled={retrying}
              className="flex-1 inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-brand-600 hover:bg-brand-500 disabled:opacity-60 text-white text-sm font-medium transition-colors"
            >
              <RefreshCw className={clsx('w-4 h-4', retrying && 'animate-spin')} />
              {retrying ? '正在重新提交…' : '重试生成'}
            </button>
            <button
              onClick={() => window.location.reload()}
              className="inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-background-elevated border border-border-subtle hover:bg-background-surface text-content-secondary text-sm font-medium transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              刷新页面
            </button>
          </div>
        )}

        {hasSteps && (
          <div className="space-y-2">
            {steps.map((step, idx) => {
              const effectiveIndex = isQueued || isWaiting || isStalled ? -1 : currentStepIndex;
              const isCurrent = idx === effectiveIndex;
              const isDone = idx < effectiveIndex;
              return (
                <div
                  key={step.id}
                  className={clsx(
                    'flex items-start gap-3 p-3 rounded-lg text-sm transition-colors',
                    isCurrent
                      ? 'bg-brand-900/20 border border-brand-500/20'
                      : 'border border-transparent',
                    isDone ? 'text-content-secondary' : 'text-content-tertiary'
                  )}
                >
                  <div className="mt-0.5 shrink-0">
                    {isDone ? (
                      <Check className="w-4 h-4 text-success" />
                    ) : isCurrent ? (
                      <Loader2 className="w-4 h-4 text-brand-400 animate-spin" />
                    ) : (
                      <Circle className="w-4 h-4" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className={clsx('font-medium', isCurrent && 'text-content-primary')}>
                      {step.label}
                    </div>
                    <div className="text-xs mt-0.5">{STEP_DETAILS[step.id]}</div>
                    {isCurrent && (
                      <div className="text-xs text-brand-400 mt-1 font-medium">
                        正在执行{'.'.repeat((tick % 3) + 1)}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
