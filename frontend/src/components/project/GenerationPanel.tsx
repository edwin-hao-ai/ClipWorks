'use client';

import { useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/Button';
import { api } from '@/lib/api';
import { Project, RenderJob } from '@/lib/types';
import { Sparkles } from 'lucide-react';

interface Props {
  projectId: string;
  status: Project['status'];
  onStatusChange: (status: Project['status']) => void;
  onJobComplete?: (job: RenderJob) => void;
}

export function GenerationPanel({ projectId, status, onStatusChange, onJobComplete }: Props) {
  const [job, setJob] = useState<RenderJob | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [prompt, setPrompt] = useState('');
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const unmountedRef = useRef(false);

  const stopPolling = () => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
  };

  useEffect(() => {
    unmountedRef.current = false;
    return () => {
      unmountedRef.current = true;
      stopPolling();
    };
  }, []);

  const pollJob = async (jobId: string) => {
    if (unmountedRef.current) return;
    try {
      const j = await api.get(`/projects/${projectId}/renders/${jobId}`);
      if (unmountedRef.current) return;
      setJob(j);
      if (j.status === 'completed' || j.status === 'failed') {
        onStatusChange(j.status === 'completed' ? 'ready' : 'failed');
        if (j.status === 'completed') {
          onJobComplete?.(j);
        }
        if (j.status === 'failed') {
          setError(j.error_message || '生成失败，请重试');
        }
        setLoading(false);
      } else {
        timeoutRef.current = setTimeout(() => pollJob(jobId), 1000);
      }
    } catch (err) {
      if (unmountedRef.current) return;
      simulateDemoGeneration();
    }
  };

  const generate = async () => {
    if (unmountedRef.current) return;
    setJob(null);
    setLoading(true);
    setError(null);
    stopPolling();

    try {
      const data = prompt.trim()
        ? await api.post(`/projects/${projectId}/renders/agent-generate`, { prompt })
        : await api.post(`/projects/${projectId}/renders/generate`);
      const jobId: string = data.job_id;
      if (unmountedRef.current) return;
      onStatusChange('generating');
      timeoutRef.current = setTimeout(() => pollJob(jobId), 1000);
    } catch (err) {
      if (unmountedRef.current) return;
      simulateDemoGeneration();
    }
  };

  const simulateDemoGeneration = () => {
    onStatusChange('generating');
    let progress = 0;
    const interval = setInterval(() => {
      if (unmountedRef.current) {
        clearInterval(interval);
        return;
      }
      progress += 10;
      setJob({ id: 'demo-job', status: 'processing', progress } as RenderJob);
      if (progress >= 100) {
        clearInterval(interval);
        const completedJob: RenderJob = {
          id: 'demo-job',
          status: 'completed',
          progress: 100,
          output_url: '/api/static/demo-output.mp4',
          html_output_url: '/api/static/demo-output.html',
        };
        setJob(completedJob);
        onStatusChange('ready');
        onJobComplete?.(completedJob);
        setLoading(false);
      }
    }, 400);
  };

  return (
    <div className="bg-background-surface border border-border-subtle rounded-md p-5">
      <h3 className="font-semibold text-content-primary mb-4 flex items-center gap-2">
        <Sparkles className="w-4 h-4 text-brand-400" /> 生成视频
      </h3>
      {status === 'ready' ? (
        <div className="text-success bg-success/10 border border-success/20 px-4 py-3 rounded-md text-sm mb-4">
          视频已生成完成
        </div>
      ) : status === 'generating' ? (
        <div className="text-warning bg-warning/10 border border-warning/20 px-4 py-3 rounded-md text-sm mb-4">
          <div className="flex justify-between mb-2">
            <span>正在生成中…</span>
            <span className="font-mono">{job?.progress || 0}%</span>
          </div>
          <div className="w-full bg-background-elevated h-2 rounded-full overflow-hidden">
            <div
              className="relative h-full bg-warning rounded-full transition-all duration-300 ease-out overflow-hidden"
              style={{ width: `${job?.progress || 0}%` }}
            >
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-shimmer" />
            </div>
          </div>
        </div>
      ) : null}
      {(error || status === 'failed') && (
        <div className="text-error bg-error/10 border border-error/20 px-4 py-3 rounded-md text-sm mb-4">
          {error || '生成失败，请重试'}
        </div>
      )}
      <div className="space-y-3 mb-4">
        <label className="block text-xs text-content-secondary">
          生成提示（可选）
          <input
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="例如：更活泼一点、针对年轻人…"
            disabled={loading || status === 'generating'}
            className="mt-1 w-full bg-background-elevated border border-border-subtle rounded-md px-3 py-2 text-sm text-content-primary placeholder-content-tertiary focus:outline-none focus:border-brand-500 disabled:opacity-50"
          />
        </label>
      </div>
      <Button
        onClick={generate}
        disabled={loading || status === 'generating'}
        className={`w-full ${status === 'generating' ? 'animate-pulseGlow' : ''}`}
      >
        <Sparkles className="w-4 h-4 mr-1.5" />
        {status === 'ready' ? '重新生成' : '开始生成'}
      </Button>
    </div>
  );
}
