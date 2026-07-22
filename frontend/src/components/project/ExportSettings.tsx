'use client';

import { useEffect, useState } from 'react';
import { clsx } from 'clsx';
import { Button } from '@/components/ui/Button';
import { api } from '@/lib/api';
import { Project } from '@/lib/types';
import { Download, Loader2, Monitor, Smartphone, Square, X, HardDrive, Cloud } from 'lucide-react';

interface ExportSettingsProps {
  project: Project;
  open: boolean;
  onClose: () => void;
  onStart?: () => void;
}

type ExportFormat = '16:9' | '9:16' | '1:1';
type ExportQuality = 'standard' | 'high' | 'ultra';
type ExportLocation = 'local' | 'cloud';

const FORMAT_OPTIONS: { value: ExportFormat; label: string; icon: React.ReactNode }[] = [
  { value: '16:9', label: '横屏 16:9', icon: <Monitor className="w-4 h-4" /> },
  { value: '9:16', label: '竖屏 9:16', icon: <Smartphone className="w-4 h-4" /> },
  { value: '1:1', label: '方形 1:1', icon: <Square className="w-4 h-4" /> },
];

const QUALITY_OPTIONS: { value: ExportQuality; label: string; description: string }[] = [
  { value: 'standard', label: '标准', description: '720p / 较快' },
  { value: 'high', label: '高清', description: '1080p / 推荐' },
  { value: 'ultra', label: '超清', description: '2K+ / 较慢' },
];

const LOCATION_OPTIONS: { value: ExportLocation; label: string; icon: React.ReactNode }[] = [
  { value: 'local', label: '本地下载', icon: <HardDrive className="w-4 h-4" /> },
  { value: 'cloud', label: '云端存储', icon: <Cloud className="w-4 h-4" /> },
];

export function ExportSettings({ project, open, onClose, onStart }: ExportSettingsProps) {
  const [targetFormat, setTargetFormat] = useState<ExportFormat>(
    (['16:9', '9:16', '1:1'].includes(project.target_format) ? project.target_format : '16:9') as ExportFormat
  );
  const [targetDuration, setTargetDuration] = useState<number | ''>(project.target_duration ?? 30);
  const [quality, setQuality] = useState<ExportQuality>('high');
  const [location, setLocation] = useState<ExportLocation>('local');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const parsedDuration =
    targetDuration === '' ? NaN : typeof targetDuration === 'number' ? targetDuration : parseInt(targetDuration, 10);
  const durationValid = !isNaN(parsedDuration) && parsedDuration >= 5 && parsedDuration <= 300;
  const durationError = targetDuration === '' || !durationValid;

  // 打开时重置为当前项目值，避免残留旧状态。
  useEffect(() => {
    if (open) {
      setTargetFormat(
        (['16:9', '9:16', '1:1'].includes(project.target_format) ? project.target_format : '16:9') as ExportFormat
      );
      setTargetDuration(project.target_duration ?? 30);
      setError(null);
    }
  }, [open, project.target_format, project.target_duration]);

  // Esc 关闭（提交中禁用）。
  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !submitting) onClose();
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [open, submitting, onClose]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (submitting || !durationValid) return;

    const duration = parsedDuration;
    setError(null);
    setSubmitting(true);

    try {
      // 1. 先同步项目的画幅与时长设置。
      await api.put(`/projects/${project.id}`, {
        target_format: targetFormat,
        target_duration: duration,
      });

      // 2. 触发渲染；quality 透传给后端，映射到 HyperFrames --quality / --resolution。
      await api.post(`/projects/${project.id}/renders/generate`, { quality });

      onStart?.();
      onClose();
    } catch (err) {
      const msg = err instanceof Error ? err.message : '导出失败';
      if (msg.includes('402')) {
        setError('额度不足：前往计费页切换套餐即可补充额度（演示环境）。');
      } else {
        setError(msg);
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 animate-fadeIn"
      onClick={() => {
        if (!submitting) onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="export-settings-title"
    >
      <div
        className="bg-background-elevated border border-border-default rounded-xl w-full max-w-md shadow-lg p-6 animate-modalIn"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-5">
          <h2 id="export-settings-title" className="text-lg font-semibold text-content-primary">
            导出设置
          </h2>
          <button
            type="button"
            onClick={onClose}
            disabled={submitting}
            className="text-content-tertiary hover:text-content-primary transition-colors disabled:opacity-50"
            aria-label="关闭"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="block text-sm font-medium text-content-secondary mb-2">画幅比例</label>
            <div className="grid grid-cols-3 gap-2">
              {FORMAT_OPTIONS.map((fmt) => (
                <button
                  key={fmt.value}
                  type="button"
                  onClick={() => setTargetFormat(fmt.value)}
                  className={clsx(
                    'flex flex-col items-center gap-1.5 px-3 py-2.5 rounded-lg border text-xs font-medium transition-colors',
                    targetFormat === fmt.value
                      ? 'bg-brand-900/30 border-brand-500/50 text-brand-400'
                      : 'bg-background-surface border-border-subtle text-content-secondary hover:border-brand-500/30 hover:text-content-primary'
                  )}
                >
                  {fmt.icon}
                  {fmt.label}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label htmlFor="export-duration" className="block text-sm font-medium text-content-secondary mb-2">
              目标时长（秒）
            </label>
            <input
              id="export-duration"
              type="number"
              value={targetDuration}
              onChange={(e) => setTargetDuration(e.target.value === '' ? '' : parseInt(e.target.value, 10))}
              aria-invalid={durationError}
              aria-describedby={durationError ? 'export-duration-error' : undefined}
              className={clsx(
                'w-full bg-background-surface border rounded-lg px-3 py-2 text-sm text-content-primary outline-none focus:border-brand-500 transition-colors',
                durationError
                  ? 'border-error focus:border-error'
                  : 'border-border-default'
              )}
            />
            {durationError && (
              <p id="export-duration-error" className="mt-1.5 text-xs text-error">
                目标时长需在 5–300 秒之间
              </p>
            )}
          </div>

          <div>
            <label className="block text-sm font-medium text-content-secondary mb-2">导出质量</label>
            <div className="grid grid-cols-3 gap-2">
              {QUALITY_OPTIONS.map((q) => (
                <button
                  key={q.value}
                  type="button"
                  onClick={() => setQuality(q.value)}
                  className={clsx(
                    'flex flex-col items-center gap-1 px-3 py-2.5 rounded-lg border text-xs transition-colors',
                    quality === q.value
                      ? 'bg-brand-900/30 border-brand-500/50 text-brand-400'
                      : 'bg-background-surface border-border-subtle text-content-secondary hover:border-brand-500/30 hover:text-content-primary'
                  )}
                >
                  <span className="font-medium">{q.label}</span>
                  <span className="text-[10px] opacity-80">{q.description}</span>
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-content-secondary mb-2">保存位置</label>
            <div className="grid grid-cols-2 gap-2">
              {LOCATION_OPTIONS.map((loc) => (
                <button
                  key={loc.value}
                  type="button"
                  onClick={() => setLocation(loc.value)}
                  className={clsx(
                    'flex items-center justify-center gap-2 px-3 py-2.5 rounded-lg border text-xs font-medium transition-colors',
                    location === loc.value
                      ? 'bg-brand-900/30 border-brand-500/50 text-brand-400'
                      : 'bg-background-surface border-border-subtle text-content-secondary hover:border-brand-500/30 hover:text-content-primary'
                  )}
                >
                  {loc.icon}
                  {loc.label}
                </button>
              ))}
            </div>
            <p className="mt-1.5 text-[11px] text-content-tertiary">
              云存储将在后续版本支持，当前仅作为 UI 状态保留。
            </p>
          </div>

          {error && (
            <div data-testid="export-error" className="text-sm text-error bg-error/10 border border-error/20 rounded-md px-4 py-3">
              {error}
            </div>
          )}

          <div className="flex items-center justify-end gap-3 pt-1">
            <Button type="button" variant="ghost" onClick={onClose} disabled={submitting}>
              取消
            </Button>
            <Button type="submit" disabled={submitting || !durationValid}>
              {submitting ? (
                <span className="flex items-center gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  开始导出…
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <Download className="w-4 h-4" />
                  开始导出
                </span>
              )}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
