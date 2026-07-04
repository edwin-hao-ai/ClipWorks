'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { api } from '@/lib/api';
import { RenderJob } from '@/lib/types';

interface Props {
  projectId: string;
  status: string;
  onStatusChange: (status: string) => void;
}

export function GenerationPanel({ projectId, status, onStatusChange }: Props) {
  const [job, setJob] = useState<RenderJob | null>(null);
  const [loading, setLoading] = useState(false);

  const generate = async () => {
    setLoading(true);
    const data = await api.post(`/projects/${projectId}/renders/generate`);
    const jobId = data.job_id;
    onStatusChange('generating');

    const poll = setInterval(async () => {
      const j = await api.get(`/projects/${projectId}/renders/${jobId}`);
      setJob(j);
      if (j.status === 'completed' || j.status === 'failed') {
        clearInterval(poll);
        onStatusChange(j.status === 'completed' ? 'ready' : 'failed');
        setLoading(false);
      }
    }, 1000);
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
      <Button onClick={generate} disabled={loading || status === 'generating'} className="w-full">
        {status === 'ready' ? '重新生成' : '开始生成'}
      </Button>
    </div>
  );
}
