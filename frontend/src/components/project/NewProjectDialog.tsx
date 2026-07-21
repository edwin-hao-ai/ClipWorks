'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/Button';
import { api } from '@/lib/api';
import { Project } from '@/lib/types';
import {
  QUICK_PROMPTS,
  extractDuration,
  extractFormat,
  extractUrl,
  makeProjectTitle,
} from '@/lib/projectIntent';
import { Paperclip, Plus, Sparkles, X } from 'lucide-react';

interface Props {
  onCreated?: () => void;
  trigger?: (open: () => void) => React.ReactNode;
}

export function NewProjectDialog({ onCreated, trigger }: Props) {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [prompt, setPrompt] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const promptRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  // 打开即聚焦输入框——对话式创建应让光标直接落在 prompt 上。
  useEffect(() => {
    if (open) {
      const t = setTimeout(() => promptRef.current?.focus(), 50);
      return () => clearTimeout(t);
    }
  }, [open]);

  // Esc 关闭对话框（提交中屏蔽，避免误关导致状态丢失）；遮罩本身无键盘焦点，
  // 键盘事件必须挂在 document 上才能稳定捕获。
  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !submitting) setOpen(false);
    };
    document.addEventListener('keydown', onKeyDown);
    return () => document.removeEventListener('keydown', onKeyDown);
  }, [open, submitting]);

  const reset = () => {
    setPrompt('');
    setFile(null);
    setError(null);
  };

  const submit = async () => {
    const text = prompt.trim();
    if (!text && !file) {
      setError('先描述一下你想做的视频，或附加一个素材文件');
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      const sourceUrl = text ? extractUrl(text) : undefined;
      const project = (await api.post('/projects/', {
        title: text ? makeProjectTitle(text) : (file?.name.slice(0, 80) || '未命名项目'),
        source_url: sourceUrl || '',
        source_type: file ? 'upload' : 'url',
        target_format: text ? extractFormat(text) : undefined,
        target_duration: text ? extractDuration(text) : undefined,
      })) as Project;

      // 附加了素材：项目创建后把文件落到该项目的素材库，后续渲染可直接引用。
      if (file) {
        const form = new FormData();
        form.append('file', file);
        await api.postForm(`/projects/${project.id}/assets/`, form);
      }

      // 没有文字描述时，给 Agent 一个基于文件名的初始指令，规划对话不冷启动。
      const initialPrompt = text || `用我上传的素材「${file?.name}」做一个视频`;

      setOpen(false);
      reset();
      onCreated?.();
      router.push(`/projects/${project.id}?initialPrompt=${encodeURIComponent(initialPrompt)}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建项目失败');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <>
      {trigger ? (
        trigger(() => setOpen(true))
      ) : (
        <Button onClick={() => setOpen(true)}>
          <span className="flex items-center gap-2">
            <Plus className="w-4 h-4" />
            新建项目
          </span>
        </Button>
      )}
      {open && (
        <div
          className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 animate-fadeIn"
          data-testid="new-project-backdrop"
          onClick={() => {
            // 点遮罩空白处关闭；提交中禁用，防止请求在途时界面被误关
            if (!submitting) setOpen(false);
          }}
        >
          <div
            className="bg-background-elevated border border-border-default rounded-lg w-full max-w-lg shadow-lg p-6 animate-modalIn"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-semibold text-content-primary">新建项目</h2>
              <button
                onClick={() => setOpen(false)}
                className="text-content-tertiary hover:text-content-primary transition-colors"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-sm text-content-secondary mb-4">
              描述你的视频想法，AI 会自动规划并生成成片。
            </p>
            <div className="bg-background-base border border-border-default rounded-2xl p-2 flex items-center gap-2 shadow-glow focus-within:border-brand-500 transition-colors mb-3">
              <input
                ref={promptRef}
                data-testid="new-project-prompt"
                type="text"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                onKeyDown={(e) => {
                  // Enter 直接开聊
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    if (!submitting) submit();
                  }
                }}
                placeholder="例如：帮我做一个 30 秒的产品介绍视频，9:16，风格活泼，面向年轻人…"
                className="flex-1 min-w-0 bg-transparent px-4 py-3 text-base outline-none placeholder:text-content-tertiary text-content-primary"
              />
              <Button
                data-testid="new-project-submit"
                onClick={submit}
                disabled={submitting || (!prompt.trim() && !file)}
                size="lg"
                className="shrink-0 px-3 sm:px-5"
              >
                {submitting ? (
                  <span className="flex items-center gap-2">
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    创建中
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4" />
                    开始创作
                  </span>
                )}
              </Button>
            </div>

            <div className="flex flex-wrap gap-1.5">
              {QUICK_PROMPTS.map((p) => (
                <button
                  key={p}
                  type="button"
                  onClick={() => setPrompt(p)}
                  disabled={submitting}
                  className="focus-ring px-2.5 py-1 rounded-full bg-background-surface border border-border-subtle text-xs text-content-secondary hover:border-brand-500/50 hover:text-brand-400 transition-colors disabled:opacity-50"
                >
                  {p}
                </button>
              ))}
            </div>

            <input
              ref={fileRef}
              type="file"
              data-testid="new-project-file"
              accept="video/*,image/*,audio/*"
              className="hidden"
              onChange={(e) => {
                setFile(e.target.files?.[0] || null);
                setError(null);
              }}
            />
            <div className="mt-4 flex items-center gap-2">
              <button
                type="button"
                onClick={() => fileRef.current?.click()}
                className="flex-1 flex items-center gap-2 px-3 py-2 rounded-md border border-dashed border-border-default text-xs text-content-secondary hover:border-brand-500/60 hover:text-content-primary transition-colors"
              >
                <Paperclip className="w-3.5 h-3.5 shrink-0" />
                {file ? (
                  <span className="truncate text-content-primary">{file.name}</span>
                ) : (
                  <span>附加素材文件（可选）· MP4/MOV/PNG/JPG，≤50MB</span>
                )}
              </button>
              {file && (
                <button
                  type="button"
                  onClick={() => {
                    setFile(null);
                    if (fileRef.current) fileRef.current.value = '';
                  }}
                  aria-label="移除素材文件"
                  className="shrink-0 p-1.5 rounded-md text-content-tertiary hover:text-error hover:bg-error/10 transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>

            {error && (
              <div className="mt-4 text-sm text-error bg-error/10 border border-error/20 rounded-md px-4 py-3">
                {error}
              </div>
            )}

            <div className="flex justify-end mt-6">
              <Button variant="ghost" onClick={() => setOpen(false)} disabled={submitting}>
                取消
              </Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
