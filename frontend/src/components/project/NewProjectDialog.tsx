'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { api } from '@/lib/api';

interface Props {
  onCreated: () => void;
}

export function NewProjectDialog({ onCreated }: Props) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState('');
  const [sourceUrl, setSourceUrl] = useState('');
  const [sourceType, setSourceType] = useState<'url' | 'upload'>('url');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    setError(null);
    setSubmitting(true);
    try {
      await api.post('/projects/', {
        title: title || '未命名项目',
        source_url: sourceType === 'url' ? sourceUrl : undefined,
        source_type: sourceType,
      });
      setOpen(false);
      setTitle('');
      setSourceUrl('');
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建项目失败');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      <Button onClick={() => setOpen(true)}>新建项目</Button>
      {open && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl w-full max-w-lg p-6">
            <h2 className="text-lg font-semibold mb-4">新建项目</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">项目名称</label>
                <input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg"
                  placeholder="例如：产品发布视频"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">来源类型</label>
                <div className="flex gap-2">
                  <button
                    onClick={() => setSourceType('url')}
                    className={`px-4 py-2 rounded-lg text-sm border ${
                      sourceType === 'url' ? 'border-brand-600 text-brand-600 bg-brand-50' : 'border-slate-200'
                    }`}
                  >
                    官网链接
                  </button>
                  <button
                    onClick={() => setSourceType('upload')}
                    className={`px-4 py-2 rounded-lg text-sm border ${
                      sourceType === 'upload' ? 'border-brand-600 text-brand-600 bg-brand-50' : 'border-slate-200'
                    }`}
                  >
                    上传视频
                  </button>
                </div>
              </div>
              {sourceType === 'url' && (
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">官网链接</label>
                  <input
                    value={sourceUrl}
                    onChange={(e) => setSourceUrl(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg"
                    placeholder="https://your-product.com"
                  />
                </div>
              )}
              {sourceType === 'upload' && (
                <div className="border-2 border-dashed border-slate-200 rounded-lg p-8 text-center text-slate-500">
                  上传功能在素材库中使用
                </div>
              )}
            </div>
            {error && (
              <div className="mt-4 text-sm text-red-700 bg-red-50 rounded-lg px-4 py-3">
                {error}
              </div>
            )}
            <div className="flex justify-end gap-3 mt-6">
              <Button variant="ghost" onClick={() => setOpen(false)} disabled={submitting}>
                取消
              </Button>
              <Button onClick={submit} disabled={submitting}>
                {submitting ? '创建中…' : '创建'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
