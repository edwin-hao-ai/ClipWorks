'use client';

import { useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/Button';
import { api } from '@/lib/api';
import { Project, RenderJob } from '@/lib/types';

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

  const generate = async () => {
    if (unmountedRef.current) return;
    setJob(null);
    setLoading(true);
    setError(null);
    stopPolling();

    try {
      const data = await api.post(`/projects/${projectId}/renders/generate`);
      const jobId: string = data.job_id;
      if (unmountedRef.current) return;
      onStatusChange('generating');

      const poll = async () => {
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
            timeoutRef.current = setTimeout(poll, 1000);
          }
        } catch (err) {
          if (unmountedRef.current) return;
          setLoading(false);
          setError(err instanceof Error ? err.message : '轮询任务状态失败');
          onStatusChange('failed');
        }
      };

      timeoutRef.current = setTimeout(poll, 1000);
    } catch (err) {
      if (unmountedRef.current) return;
      setLoading(false);
      setError(err instanceof Error ? err.message : '启动生成失败');
    }
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <h3 className="font-semibold text-slate-900 mb-4">生成视频</h3>
      {status === 'ready' ? (
        <div className="text-green-700 bg-green-50 px-4 py-3 rounded-lg text-sm mb-4">
          视频已生成完成
        </div>
      ) : status === 'generating' ? (
        <div className="text-amber-700 bg-amber-50 px-4 py-3 rounded-lg text-sm mb-4">
          正在生成中… {job?.progress || 0}%
          <div className="w-full bg-amber-200 h-2 rounded-full mt-2">
            <div
              className="bg-amber-500 h-2 rounded-full transition-all"
              style={{ width: `${job?.progress || 0}%` }}
            />
          </div>
        </div>
      ) : null}
      {(error || status === 'failed') && (
        <div className="text-red-700 bg-red-50 px-4 py-3 rounded-lg text-sm mb-4">
          {error || '生成失败，请重试'}
        </div>
      )}
      <Button onClick={generate} disabled={loading || status === 'generating'} className="w-full">
        {status === 'ready' ? '重新生成' : '开始生成'}
      </Button>
    </div>
  );
}
