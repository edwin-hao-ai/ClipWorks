'use client';

import { useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/Button';
import { api } from '@/lib/api';
import { Project, RenderJob } from '@/lib/types';

interface Props {
  projectId: string;
  status: Project['status'];
  onStatusChange: (status: Project['status']) => void;
}

export function GenerationPanel({ projectId, status, onStatusChange }: Props) {
  const [job, setJob] = useState<RenderJob | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    };
  }, []);

  const stopPolling = () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  };

  const generate = async () => {
    setLoading(true);
    setError(null);
    stopPolling();

    try {
      const data = await api.post(`/projects/${projectId}/renders/generate`);
      const jobId = data.job_id;
      onStatusChange('generating');

      pollRef.current = setInterval(async () => {
        try {
          const j = await api.get(`/projects/${projectId}/renders/${jobId}`);
          setJob(j);
          if (j.status === 'completed' || j.status === 'failed') {
            stopPolling();
            onStatusChange(j.status === 'completed' ? 'ready' : 'failed');
            if (j.status === 'failed' && j.error_message) {
              setError(j.error_message);
            }
            setLoading(false);
          }
        } catch (err) {
          stopPolling();
          setLoading(false);
          setError(err instanceof Error ? err.message : '轮询任务状态失败');
          onStatusChange('failed');
        }
      }, 1000);
    } catch (err) {
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
      ) : status === 'failed' ? (
        <div className="text-red-700 bg-red-50 px-4 py-3 rounded-lg text-sm mb-4">
          生成失败，请重试
        </div>
      ) : null}
      {error && (
        <div className="text-red-700 bg-red-50 px-4 py-3 rounded-lg text-sm mb-4">
          {error}
        </div>
      )}
      <Button onClick={generate} disabled={loading || status === 'generating'} className="w-full">
        {status === 'ready' ? '重新生成' : '开始生成'}
      </Button>
    </div>
  );
}
