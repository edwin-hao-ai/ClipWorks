'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { api } from '@/lib/api';
import { X, Upload, Link as LinkIcon } from 'lucide-react';

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
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 animate-fadeIn">
          <div className="bg-background-elevated border border-border-default rounded-lg w-full max-w-lg shadow-lg p-6 animate-modalIn">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-semibold text-content-primary">新建项目</h2>
              <button
                onClick={() => setOpen(false)}
                className="text-content-tertiary hover:text-content-primary transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-content-secondary mb-1.5">项目名称</label>
                <input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full px-3 py-2.5 bg-background-base border border-border-default rounded-md text-content-primary placeholder:text-content-tertiary focus:outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 transition-all"
                  placeholder="例如：产品发布视频"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-content-secondary mb-1.5">来源类型</label>
                <div className="flex gap-2">
                  <button
                    onClick={() => setSourceType('url')}
                    className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm border transition-colors ${
                      sourceType === 'url'
                        ? 'border-brand-500 text-brand-400 bg-brand-900/40'
                        : 'border-border-default text-content-secondary hover:bg-background-hover'
                    }`}
                  >
                    <LinkIcon className="w-4 h-4" /> 官网链接
                  </button>
                  <button
                    onClick={() => setSourceType('upload')}
                    className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm border transition-colors ${
                      sourceType === 'upload'
                        ? 'border-brand-500 text-brand-400 bg-brand-900/40'
                        : 'border-border-default text-content-secondary hover:bg-background-hover'
                    }`}
                  >
                    <Upload className="w-4 h-4" /> 上传视频
                  </button>
                </div>
              </div>
              {sourceType === 'url' && (
                <div>
                  <label className="block text-sm font-medium text-content-secondary mb-1.5">官网链接</label>
                  <input
                    value={sourceUrl}
                    onChange={(e) => setSourceUrl(e.target.value)}
                    className="w-full px-3 py-2.5 bg-background-base border border-border-default rounded-md text-content-primary placeholder:text-content-tertiary focus:outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20 transition-all"
                    placeholder="https://your-product.com"
                  />
                </div>
              )}
              {sourceType === 'upload' && (
                <div className="border-2 border-dashed border-border-default rounded-md p-10 text-center text-content-tertiary bg-background-base hover:border-border-default hover:bg-background-hover transition-colors cursor-pointer">
                  <Upload className="w-8 h-8 mx-auto mb-2" />
                  <p className="text-sm">上传功能在素材库中使用</p>
                </div>
              )}
            </div>
            {error && (
              <div className="mt-4 text-sm text-error bg-error/10 border border-error/20 rounded-md px-4 py-3">
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
