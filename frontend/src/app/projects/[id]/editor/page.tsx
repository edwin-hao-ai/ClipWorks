'use client';

import { useEffect, useRef, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { AuthGuard } from '@/components/layout/AuthGuard';
import { Timeline } from '@/components/editor/Timeline';
import { ClipInspector } from '@/components/editor/ClipInspector';
import { PreviewPlayer } from '@/components/project/PreviewPlayer';
import { Clip, Composition, Project, RenderJob, Track } from '@/lib/types';
import { api, API_URL } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { ArrowLeft, Save, Check, AlertCircle, Undo2, Redo2, Scissors } from 'lucide-react';

const DEFAULT_CLIP_DURATION = 3;
const HISTORY_LIMIT = 50;

function generateClipId(): string {
  return `clip-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function cloneObj<T>(x: T): T {
  return JSON.parse(JSON.stringify(x)) as T;
}

const round1 = (v: number) => Math.round(v * 10) / 10;

// 同轨片段不允许重叠：逐轨按 start_time 排序，把任何与前一段重叠的片段平移到前一段末端，
// 保持各片段 duration 不变；保留片段之间的间隙；跨轨（如 overlay 叠画面）不处理。
// 无重叠时返回原引用，避免给撤销栈引入空操作。
function resolveCollisions(comp: Composition): Composition {
  let compChanged = false;
  const tracks = comp.tracks.map((track) => {
    if (track.clips.length < 2) return track;
    const sorted = track.clips.slice().sort((a, b) => a.start_time - b.start_time);
    let end = -Infinity;
    let changed = false;
    const adjusted: Clip[] = sorted.map((c) => {
      const s = end === -Infinity ? c.start_time : round1(Math.max(c.start_time, end));
      if (s !== c.start_time) changed = true;
      end = s + c.duration;
      return s === c.start_time ? c : { ...c, start_time: s };
    });
    if (!changed) return track;
    compChanged = true;
    return { ...track, clips: adjusted };
  });
  return compChanged ? { ...comp, tracks } : comp;
}

function makeDefaultClip(track: Track): Clip {
  const lastEnd = track.clips.reduce(
    (max, c) => Math.max(max, (c.start_time || 0) + (c.duration || 0)),
    0,
  );
  const base: Clip = { id: generateClipId(), start_time: lastEnd, duration: DEFAULT_CLIP_DURATION };
  if (track.type === 'text' || track.type === 'overlay') {
    return { ...base, text_content: '新文本' };
  }
  return base;
}

export default function EditorPage() {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [composition, setComposition] = useState<Composition | null>(null);
  const [latestJob, setLatestJob] = useState<RenderJob | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveStatus, setSaveStatus] = useState<'idle' | 'success' | 'error'>('idle');
  const [selectedClipId, setSelectedClipId] = useState<string>();
  const [currentTime, setCurrentTime] = useState(0);
  const [past, setPast] = useState<Composition[]>([]);
  const [future, setFuture] = useState<Composition[]>([]);
  // 最新合成的引用，供撤销/重做同步读取，避免在函数式更新里嵌套 setState 导致批次错乱。
  const compRef = useRef<Composition | null>(null);
  // 每次渲染都把最新合成同步写入 ref（渲染体内同步赋值，幂等、Strict Mode 安全），
  // 这样「保存」读取 compRef.current 永远拿到最近一次渲染的合成，不会被
  // useEffect 的提交后延迟或某个过期闭包里的 composition 绊倒。
  compRef.current = composition;

  // 在已加载的合成中查找某个片段，返回该片段及其所属轨道（用于类型相关编辑）。
  const findClip = (comp: Composition | null, clipId?: string) => {
    if (!comp || !clipId) return null;
    for (const track of comp.tracks) {
      const clip = track.clips.find((c) => c.id === clipId);
      if (clip) return { track, clip };
    }
    return null;
  };

  // 所有编辑都走这里：应用变更前先把当前快照压入撤销栈，并清空重做栈。
  // 变更后再统一做同轨防重叠，保证时间线不会出现同轨片段互相覆盖。
  const apply = (recipe: (prev: Composition) => Composition) => {
    setComposition((prev) => {
      if (!prev) return prev;
      const next = resolveCollisions(recipe(prev));
      if (next === prev) return prev;
      setPast((p) => [...p.slice(-(HISTORY_LIMIT - 1)), cloneObj(prev)]);
      setFuture([]);
      return next;
    });
    setSaveStatus('idle');
  };

  const updateClip = (clipId: string, patch: Partial<Clip>) =>
    apply((prev) => ({
      ...prev,
      tracks: prev.tracks.map((track) => ({
        ...track,
        clips: track.clips.map((clip) => (clip.id === clipId ? { ...clip, ...patch } : clip)),
      })),
    }));

  const deleteClip = (clipId: string) => {
    setSelectedClipId(undefined);
    apply((prev) => ({
      ...prev,
      tracks: prev.tracks.map((track) => ({
        ...track,
        clips: track.clips.filter((clip) => clip.id !== clipId),
      })),
    }));
  };

  const addClip = (trackId: string) =>
    apply((prev) => ({
      ...prev,
      tracks: prev.tracks.map((track) =>
        track.id === trackId ? { ...track, clips: [...track.clips, makeDefaultClip(track)] } : track,
      ),
    }));

  // 在播放头位置把选中片段切成两段（仅当播放头落在片段内部时生效）。
  const splitSelected = () => {
    if (!composition) return;
    const found = findClip(composition, selectedClipId);
    if (!found) return;
    const { track, clip } = found;
    const t = currentTime;
    if (t <= clip.start_time + 0.05 || t >= clip.start_time + clip.duration - 0.05) return;
    const firstDur = round1(t - clip.start_time);
    const secondDur = round1(clip.duration - firstDur);
    const second: Clip = {
      ...cloneObj(clip),
      id: generateClipId(),
      start_time: round1(t),
      duration: secondDur,
    };
    apply((prev) => ({
      ...prev,
      tracks: prev.tracks.map((tr) =>
        tr.id !== track.id
          ? tr
          : {
              ...tr,
              clips: tr.clips.flatMap((c) =>
                c.id === clip.id ? [{ ...c, duration: firstDur }, second] : [c],
              ),
            },
      ),
    }));
    setSelectedClipId(second.id);
  };

  const undo = () => {
    setPast((p) => {
      if (p.length === 0) return p;
      const last = p[p.length - 1];
      const cur = compRef.current;
      if (cur) setFuture((f) => [cloneObj(cur), ...f].slice(0, HISTORY_LIMIT));
      setComposition(last);
      return p.slice(0, -1);
    });
    setSaveStatus('idle');
  };

  const redo = () => {
    setFuture((f) => {
      if (f.length === 0) return f;
      const [first, ...rest] = f;
      const cur = compRef.current;
      if (cur) setPast((p) => [...p, cloneObj(cur)].slice(-HISTORY_LIMIT));
      setComposition(first);
      return rest;
    });
    setSaveStatus('idle');
  };

  // 键盘快捷键：Ctrl/⌘+Z 撤销，Ctrl/⌘+Shift+Z 或 Ctrl+Y 重做。
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const el = e.target as HTMLElement | null;
      if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable)) return;
      const mod = e.metaKey || e.ctrlKey;
      if (!mod) return;
      const k = e.key.toLowerCase();
      if (k === 'z') {
        e.preventDefault();
        if (e.shiftKey) redo();
        else undo();
      } else if (k === 'y') {
        e.preventDefault();
        redo();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  });

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const [projectData, compositionData, jobsData] = await Promise.all([
          api.get(`/projects/${id}`),
          api.get(`/compositions/${id}`),
          api.get(`/projects/${id}/renders/`),
        ]);
        if (!cancelled) {
          setProject(projectData);
          setComposition(compositionData.error ? null : compositionData);
          const jobs = Array.isArray(jobsData) ? jobsData : [];
          setLatestJob(jobs[0] || null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : '加载编辑器失败');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    load();

    return () => {
      cancelled = true;
    };
  }, [id]);

  if (loading) {
    return (
      <AuthGuard>
        <div className="min-h-dvh flex items-center justify-center bg-background-base text-content-secondary">
          <div className="flex flex-col items-center gap-4">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500" />
            <p className="text-sm">加载编辑器中…</p>
          </div>
        </div>
      </AuthGuard>
    );
  }

  const toAbsoluteUrl = (url?: string | null) => {
    if (!url) return null;
    if (url.startsWith('http')) return url;
    return `${API_URL}${url}`;
  };

  if (error || !project || !composition) {
    return (
      <AuthGuard>
        <div className="min-h-dvh flex items-center justify-center bg-background-base">
          <div className="text-center max-w-md">
            <p className="text-error mb-4">{error || '项目或合成信息不存在'}</p>
            <Button onClick={() => window.location.reload()}>重试</Button>
          </div>
        </div>
      </AuthGuard>
    );
  }

  const selected = findClip(composition, selectedClipId);

  return (
    <AuthGuard>
      <div className="flex min-h-dvh bg-background-base">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <TopBar title={`${project.title} - 时间线编辑器`} />
          <main id="cw-main" className="flex-1 p-5 flex flex-col gap-4 overflow-hidden">
            <div className="flex items-center justify-between gap-3">
              <Link
                href={`/projects/${id}`}
                className="text-sm text-content-secondary hover:text-content-primary flex items-center gap-1 transition-colors shrink-0"
              >
                <ArrowLeft className="w-4 h-4" /> 返回工作区
              </Link>
              <div className="flex items-center gap-2 flex-wrap justify-end">
                <Button variant="secondary" size="sm" onClick={undo} disabled={past.length === 0} title="撤销 (Ctrl/⌘+Z)">
                  <Undo2 className="w-4 h-4" />
                </Button>
                <Button variant="secondary" size="sm" onClick={redo} disabled={future.length === 0} title="重做 (Ctrl/⌘+Shift+Z)">
                  <Redo2 className="w-4 h-4" />
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={splitSelected}
                  disabled={!selected}
                  title="在播放头处分割选中片段"
                >
                  <Scissors className="w-4 h-4 mr-1" /> 分割
                </Button>
                {saveStatus === 'success' && (
                  <span className="flex items-center gap-1 text-xs text-success">
                    <Check className="w-4 h-4" /> 已保存
                  </span>
                )}
                {saveStatus === 'error' && (
                  <span className="flex items-center gap-1 text-xs text-error">
                    <AlertCircle className="w-4 h-4" /> 保存失败
                  </span>
                )}
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={saving}
                  onClick={async () => {
                    // 始终保存最新合成：undo/redo 同步写 compRef，因此即便 React 尚未
                    // 把最新 composition 提交到本次渲染闭包，也能读到正确值。
                    const comp = compRef.current || composition;
                    if (!comp) return;
                    setSaving(true);
                    setSaveStatus('idle');
                    try {
                      const updated = await api.put(`/compositions/${id}`, comp);
                      setComposition(updated);
                      setSaveStatus('success');
                    } catch (err) {
                      setError(err instanceof Error ? err.message : '保存失败');
                      setSaveStatus('error');
                    } finally {
                      setSaving(false);
                      setTimeout(() => setSaveStatus('idle'), 3000);
                    }
                  }}
                >
                  {saving ? (
                    <span className="flex items-center gap-1">
                      <span className="w-3.5 h-3.5 border-2 border-current border-t-transparent rounded-full animate-spin" />
                      保存中
                    </span>
                  ) : (
                    <span className="flex items-center">
                      <Save className="w-4 h-4 mr-1.5" /> 保存
                    </span>
                  )}
                </Button>
              </div>
            </div>
            <div className="h-80 bg-black rounded-md overflow-hidden shrink-0">
              <PreviewPlayer
                outputUrl={toAbsoluteUrl(latestJob?.output_url)}
                htmlOutputUrl={toAbsoluteUrl(latestJob?.html_output_url)}
                format={(
                  ['16:9', '9:16', '1:1'].includes(project.target_format || '')
                    ? project.target_format
                    : '16:9'
                ) as '16:9' | '9:16' | '1:1'}
                isPlaceholder={
                  !!latestJob?.output_url &&
                  (latestJob.is_placeholder || latestJob.output_url.includes('/sample.mp4'))
                }
                currentTime={currentTime}
                onTimeUpdate={setCurrentTime}
              />
            </div>
            {selected && (
              <ClipInspector
                clip={selected.clip}
                trackType={selected.track.type}
                onChange={(patch) => updateClip(selected.clip.id, patch)}
                onDelete={() => deleteClip(selected.clip.id)}
              />
            )}
            <div className="flex-1 overflow-auto min-h-0">
              <Timeline
                composition={composition}
                selectedClipId={selectedClipId}
                onSelectClip={setSelectedClipId}
                onAddClip={addClip}
                onChangeClip={updateClip}
                currentTime={currentTime}
                onSeek={setCurrentTime}
              />
            </div>
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}
