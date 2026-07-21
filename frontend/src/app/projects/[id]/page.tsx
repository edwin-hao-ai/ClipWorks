'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { AuthGuard } from '@/components/layout/AuthGuard';
import { AgentChat } from '@/components/project/AgentChat';
import { AgentCanvas } from '@/components/project/AgentCanvas';
import { WorkflowStatusBar } from '@/components/project/WorkflowStatusBar';
import { AutonomySelector } from '@/components/project/AutonomySelector';
import { SceneCards } from '@/components/project/SceneCards';
import { PreviewPlayer } from '@/components/project/PreviewPlayer';
import { PropertyPanel } from '@/components/project/PropertyPanel';
import { Pipeline } from '@/components/project/Pipeline';
import { Button } from '@/components/ui/Button';
import { Composition, Project, RenderJob, Scene } from '@/lib/types';
import { api, API_URL } from '@/lib/api';
import { Download, Film, RefreshCw, Scissors, Trash2, X } from 'lucide-react';
import { clsx } from 'clsx';
import { GenerationPanel } from '@/components/project/GenerationPanel';

const PIPELINE_STEPS = [
  { id: 'understand', label: '理解需求' },
  { id: 'analyze', label: '分析素材' },
  { id: 'script', label: '编写脚本' },
  { id: 'scenes', label: '生成场景' },
  { id: 'render', label: '渲染成片' },
  { id: 'output', label: '输出成片' },
];

const SCENE_GROUP_THRESHOLD = 0.5;

function deriveScenesFromComposition(composition: Composition): Scene[] {
  // Build scenes from actual timeline clips when the backend has not produced
  // explicit scene metadata. Audio clips are treated as background and excluded
  // from the visual scene list.
  const clips: { clip: import('@/lib/types').Clip; track: import('@/lib/types').Track }[] = [];
  for (const track of composition.tracks || []) {
    if (track.type === 'audio') continue;
    for (const clip of track.clips || []) {
      clips.push({ clip, track });
    }
  }

  clips.sort((a, b) => a.clip.start_time - b.clip.start_time);

  const groups: typeof clips[] = [];
  for (const item of clips) {
    const lastGroup = groups[groups.length - 1];
    if (
      !lastGroup ||
      Math.abs(item.clip.start_time - lastGroup[0].clip.start_time) > SCENE_GROUP_THRESHOLD
    ) {
      groups.push([item]);
    } else {
      lastGroup.push(item);
    }
  }

  return groups.map((group, index) => {
    const startTime = group[0].clip.start_time;
    const endTime = Math.max(...group.map((g) => g.clip.start_time + g.clip.duration));
    const textClips = group.filter((g) => g.track.type === 'text' || g.track.type === 'overlay');
    const textContent = textClips.map((g) => g.clip.text_content).filter(Boolean).join(' ');
    const visualClip = group.find((g) => g.track.type === 'video' || g.track.type === 'image');
    const name =
      textContent.slice(0, 20) ||
      visualClip?.track.name ||
      group[0].track.name ||
      `场景 ${index + 1}`;

    return {
      id: group[0].clip.id,
      index,
      name,
      start_time: startTime,
      duration: Math.max(0.5, endTime - startTime),
      text_content: textContent,
      visual_content: visualClip?.clip.text_content,
    };
  });
}

export default function ProjectWorkspacePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();
  const initialPrompt = searchParams.get('initialPrompt') || undefined;
  const [project, setProject] = useState<Project | null>(null);
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [assets, setAssets] = useState<import('@/lib/types').MediaAsset[]>([]);
  const [selectedSceneId, setSelectedSceneId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [latestJob, setLatestJob] = useState<RenderJob | null>(null);
  const [downloading, setDownloading] = useState<{ mp4?: boolean; html?: boolean }>({});
  const [applyingScene, setApplyingScene] = useState(false);
  const [savingProject, setSavingProject] = useState(false);
  const [rerendering, setRerendering] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [credits, setCredits] = useState<number | null>(null);
  const [creditBlocked, setCreditBlocked] = useState(false);

  const handleDelete = async () => {
    if (!confirmDelete) {
      setConfirmDelete(true);
      return;
    }
    setDeleting(true);
    try {
      await api.delete(`/projects/${id}`);
      router.push('/projects');
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除项目失败');
      setDeleting(false);
      setConfirmDelete(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    api
      .get('/auth/me/stats')
      .then((data) => {
        if (!cancelled && typeof data?.remaining_credits === 'number') {
          setCredits(data.remaining_credits);
        }
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  const downloadFile = async (url: string | null | undefined, filename: string, key: 'mp4' | 'html') => {
    if (!url) return;
    setDownloading((prev) => ({ ...prev, [key]: true }));
    try {
      // Prefer the same-origin Next.js rewrite (/api/static/...) to avoid CORS
      // when fetching the file blob. If a full backend URL is given, strip the
      // API prefix and route through the frontend proxy as well.
      let fetchUrl = url;
      if (url.startsWith(`${API_URL}/api/static/`)) {
        fetchUrl = url.slice(API_URL.length);
      }
      const res = await fetch(fetchUrl, { credentials: 'include' });
      if (!res.ok) throw new Error(`下载失败: ${res.status}`);
      const blob = await res.blob();
      const blobUrl = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(blobUrl);
    } catch (err) {
      setError(err instanceof Error ? err.message : '下载失败');
    } finally {
      setDownloading((prev) => ({ ...prev, [key]: false }));
    }
  };

  const loadAssets = async () => {
    try {
      const data = await api.get(`/projects/${id}/assets/`);
      setAssets(Array.isArray(data) ? data : []);
    } catch {
      setAssets([]);
    }
  };

  // 素材库在新标签页上传后，回到工作区（标签页重新可见）时刷新右侧素材列表，
  // 否则用户必须整页刷新才能看到新上传的素材。
  useEffect(() => {
    const onVisible = () => {
      if (document.visibilityState === 'visible') loadAssets();
    };
    document.addEventListener('visibilitychange', onVisible);
    return () => document.removeEventListener('visibilitychange', onVisible);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const applyProjectData = (data: Project, assetsData: unknown) => {
    setProject(data);
    setAssets(Array.isArray(assetsData) ? assetsData : []);
    const compositionScenes = data.composition?.metadata?.scenes as Scene[] | undefined;
    if (compositionScenes?.length) {
      setScenes(compositionScenes);
    } else if (data.composition) {
      setScenes(deriveScenesFromComposition(data.composition as Composition));
    }
  };

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const [data, assetsData] = await Promise.all([
          api.get(`/projects/${id}`),
          api.get(`/projects/${id}/assets/`).catch(() => []),
        ]);
        if (cancelled) return;
        applyProjectData(data as Project, assetsData);
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : '加载项目失败');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, [id]);

  const refreshProject = async () => {
    try {
      const [data, assetsData] = await Promise.all([
        api.get(`/projects/${id}`),
        api.get(`/projects/${id}/assets/`).catch(() => []),
      ]);
      applyProjectData(data as Project, assetsData);
    } catch {
      // Ignore refresh errors to avoid disrupting the chat experience.
    }
  };

  const handleWizardStateChange = async (nextState: NonNullable<Project['agent_state']>) => {
    if (!project) return;
    const previousState = project.agent_state;
    setProject((prev) => (prev ? { ...prev, agent_state: nextState } : null));
    try {
      await api.post(`/projects/${project.id}/agent/state`, { state: nextState });
    } catch (err) {
      // 后端保存失败时回滚本地状态，避免用户看到“已保存”的假象。
      setProject((prev) => (prev ? { ...prev, agent_state: previousState } : null));
      setError(err instanceof Error ? err.message : '保存状态失败');
    }
  };

  // 用当前时间线（合成）重新触发一次渲染，便于在编辑器修改后快速出片。
  const handleRerender = async () => {
    if (!id || rerendering) return;
    setRerendering(true);
    setError(null);
    try {
      await api.post(`/projects/${id}/renders/generate`, {});
      setProject((prev) => (prev ? { ...prev, status: 'generating' } : prev));
      setTimeout(() => refreshProject(), 300);
    } catch (err) {
      const msg = err instanceof Error ? err.message : '重新渲染失败';
      if (msg.includes('402')) {
        // 额度不足：保留工作区，展示升级提示，不要让全屏错误页盖掉时间线。
        setCreditBlocked(true);
      } else {
        setError(msg);
      }
      setRerendering(false);
    }
  };

  // Fetch and poll the latest render job so the preview updates when rendering completes.
  useEffect(() => {
    if (!project) return;
    let cancelled = false;
    let timeoutId: ReturnType<typeof setTimeout> | null = null;

    const fetchLatestJob = async () => {
      try {
        const jobs: RenderJob[] = await api.get(`/projects/${project.id}/renders/`);
        if (cancelled) return;
        const latest = jobs[0] || null;
        setLatestJob(latest);
        const jobRunning =
          !!latest && (latest.status === 'queued' || latest.status === 'running');
        // 后端在任务进入终态时会把项目状态落库为 ready/failed 并扣减额度；轮询若只
        // 更新 job 而不回拉项目状态，工作区会永远停在「生成中」视图且轮询永不停止。
        if (latest && !jobRunning && project.status === 'generating') {
          refreshProject();
          api
            .get('/auth/me/stats')
            .then((data) => {
              if (!cancelled && typeof data?.remaining_credits === 'number') {
                setCredits(data.remaining_credits);
              }
            })
            .catch(() => {});
          window.dispatchEvent(new CustomEvent('cw:stats-changed'));
        }
        // Keep polling while the project is still generating or the latest job is in progress.
        const stillRunning = project.status === 'generating' || jobRunning;
        if (stillRunning) {
          timeoutId = setTimeout(fetchLatestJob, 2000);
        }
      } catch {
        // Ignore polling errors to avoid breaking the workspace.
      }
    };

    fetchLatestJob();
    return () => {
      cancelled = true;
      if (timeoutId) clearTimeout(timeoutId);
    };
  }, [project?.id, project?.status]);

  // Map project status and the latest render job progress to a pipeline step.
  // The backend now reports granular progress (10/30/50/70/100) during rendering.
  const currentStepIndex = (() => {
    if (!project) return -1;
    if (project.status === 'failed') return -1;
    if (project.status === 'ready') return PIPELINE_STEPS.length; // 全部完成，最后一步不再转圈
    if (project.status === 'draft' || project.status === 'planning') return -1;
    const progress = latestJob?.progress ?? 0;
    if (progress >= 100) return PIPELINE_STEPS.length - 1;
    if (progress >= 70) return 4; // render
    if (progress >= 50) return 3; // scenes
    if (progress >= 30) return 2; // script
    if (progress >= 10) return 1; // analyze
    return 0; // understand / queued
  })();

  const pipelineDescription: Record<Project['status'], string> = {
    draft: '等待生成',
    planning: '方案确认中',
    generating: '生成中…',
    ready: '生成完成',
    failed: '生成失败',
  };

  const previewFormat = (
    ['16:9', '9:16', '1:1'].includes(project?.target_format || '') ? project?.target_format : '16:9'
  ) as '16:9' | '9:16' | '1:1';

  // Static previews (video / HTML iframe) must go through the same-origin
  // Next.js rewrite. Pointing an <iframe> at http://localhost:8000 directly
  // is cross-origin and can be blocked, leaving a black preview box.
  const toSameOriginUrl = (url?: string | null) => {
    if (!url) return null;
    const prefix = `${API_URL}/api/static/`;
    if (url.startsWith(prefix)) return url.slice(API_URL.length);
    if (url.startsWith('/api/static/')) return url;
    return url;
  };

  const handlePropertyChange = async (changes: Partial<Project> | Partial<Scene>) => {
    if (!project) return;
    // 画幅未真正变化时不触发 Agent 渲染（避免重复点击同一画幅也排队出片）。
    if (
      'target_format' in changes &&
      changes.target_format &&
      changes.target_format !== project.target_format
    ) {
      try {
        setError(null);
        const data = await api.post(`/projects/${project.id}/agent/chat`, {
          message: `把画幅改成 ${changes.target_format}`,
          render: true,
        });
        setProject((prev) =>
          prev
            ? {
                ...prev,
                target_format: changes.target_format as string,
                composition: (data.composition as Composition) || prev.composition,
              }
            : null
        );
      } catch (err) {
        const msg = err instanceof Error ? err.message : '修改画幅失败，请重试';
        if (msg.includes('402')) setCreditBlocked(true);
        else setError(msg);
      }
      return;
    }

    // Project-level property changes (e.g. title / target_duration) update local state
    // until a re-render is triggered. Scene-level edits are handled by handleSceneApply
    // so we only update the local form here.
    if (!selectedSceneId) {
      setProject((prev) => (prev ? { ...prev, ...changes } : null));
    }
  };

  const handleSceneApply = async (changes: Partial<Scene>) => {
    if (!project || !selectedSceneId) return;
    const scene = scenes.find((s) => s.id === selectedSceneId);
    if (!scene) return;

    setApplyingScene(true);
    setError(null);
    try {
      const parts: string[] = [];
      if (changes.name !== undefined && changes.name !== scene.name) {
        parts.push(`把场景名称改成「${changes.name}」`);
      }
      if (changes.text_content !== undefined && changes.text_content !== scene.text_content) {
        parts.push(`把文案改成「${changes.text_content}」`);
      }
      if (changes.duration !== undefined && changes.duration !== scene.duration) {
        parts.push(`把时长改成 ${changes.duration} 秒`);
      }
      if (parts.length === 0) return;

      const message = parts.join('，');
      const data = await api.post(`/projects/${project.id}/agent/chat`, {
        message,
        scene_id: selectedSceneId,
        render: true,
      });
      setProject((prev) =>
        prev
          ? {
              ...prev,
              status: 'generating',
              composition: (data.composition as Composition) || prev.composition,
            }
          : null
      );
      if (data.composition) {
        const compositionScenes = data.composition.metadata?.scenes as Scene[] | undefined;
        if (compositionScenes?.length) {
          setScenes(compositionScenes);
        } else {
          setScenes(deriveScenesFromComposition(data.composition as Composition));
        }
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : '应用场景修改失败，请重试';
      if (msg.includes('402')) setCreditBlocked(true);
      else setError(msg);
    } finally {
      setApplyingScene(false);
    }
  };

  const handleProjectSave = async (changes: Partial<Project>) => {
    if (!project) return;
    setSavingProject(true);
    setError(null);
    try {
      const updated = await api.put(`/projects/${project.id}`, changes);
      setProject((prev) => (prev ? { ...prev, ...updated } : null));
      if (changes.source_url) {
        await loadAssets();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存项目属性失败');
    } finally {
      setSavingProject(false);
    }
  };

  if (loading) {
    return (
      <AuthGuard>
        <div className="min-h-dvh flex items-center justify-center bg-background-base text-content-secondary">
          <div className="flex flex-col items-center gap-4">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500" />
            <p className="text-sm">加载项目中…</p>
          </div>
        </div>
      </AuthGuard>
    );
  }

  if (!project) {
    // 仅在初次加载失败 / 项目不存在时占据全屏；动作类错误（保存、应用、重渲）
    // 在已加载的工作区内以横幅内联展示，避免一次瞬态失败就抹掉整条时间线。
    return (
      <AuthGuard>
        <div className="min-h-dvh flex items-center justify-center bg-background-base">
          <div className="text-center max-w-md">
            <p className="text-error mb-4">{error || '项目不存在'}</p>
            <Button onClick={() => window.location.reload()}>重试</Button>
          </div>
        </div>
      </AuthGuard>
    );
  }

  const isPlanning = project.status === 'draft' || project.status === 'planning';
  const isGenerating = project.status === 'generating';

  return (
    <AuthGuard>
      <div className="flex min-h-dvh bg-background-base">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <TopBar
            title={project.title}
            showBack
            backHref="/projects"
            right={
              <>
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={!latestJob?.html_output_url || downloading.html}
                  title={
                    latestJob?.html_output_url
                      ? '下载 HTML 预览文件'
                      : '尚无 HTML 预览，请先完成渲染'
                  }
                  onClick={() =>
                    downloadFile(
                      latestJob?.html_output_url,
                      `${project.title || 'project'}.html`,
                      'html'
                    )
                  }
                >
                  {downloading.html ? (
                    <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <span className="flex items-center gap-2">
                      <Download className="w-4 h-4" />
                      <span className="hidden sm:inline">导出 HTML</span>
                    </span>
                  )}
                </Button>
                <Button
                  size="sm"
                  disabled={!latestJob?.output_url || downloading.mp4}
                  title={
                    latestJob?.output_url
                      ? '下载 MP4 成片'
                      : '尚无 MP4 成片，请先完成渲染'
                  }
                  onClick={() =>
                    downloadFile(
                      latestJob?.output_url,
                      `${project.title || 'project'}.mp4`,
                      'mp4'
                    )
                  }
                >
                  {downloading.mp4 ? (
                    <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <span className="flex items-center gap-2">
                      <Download className="w-4 h-4" />
                      <span className="hidden sm:inline">导出 MP4</span>
                    </span>
                  )}
                </Button>
                {confirmDelete ? (
                  <div className="flex items-center gap-1.5">
                    <span className="text-xs text-content-secondary">删除此项目？</span>
                    <Button
                      variant="secondary"
                      size="sm"
                      data-testid="confirm-delete"
                      onClick={handleDelete}
                      disabled={deleting}
                      className="text-error border-error/40 hover:bg-error/10"
                    >
                      {deleting ? (
                        <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                      ) : (
                        <span className="flex items-center gap-1.5">
                          <Trash2 className="w-4 h-4" /> 确认
                        </span>
                      )}
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      data-testid="cancel-delete"
                      onClick={() => setConfirmDelete(false)}
                      disabled={deleting}
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  </div>
                ) : (
                  <Button
                    variant="secondary"
                    size="sm"
                    data-testid="delete-project"
                    onClick={handleDelete}
                  >
                    <span className="flex items-center gap-1.5">
                      <Trash2 className="w-4 h-4" />
                      <span className="hidden sm:inline">删除</span>
                    </span>
                  </Button>
                )}
              </>
            }
          />
          <main
            id="cw-main"
            className={clsx(
              'flex-1 p-5',
              isPlanning || isGenerating
                ? 'h-[calc(100dvh-3.5rem)] overflow-hidden'
                : 'h-[calc(100dvh-3.5rem)] overflow-y-auto'
            )}
          >
            {error && (
              <div
                data-testid="action-error-banner"
                className="mb-4 flex items-center justify-between gap-3 rounded-md border border-error/30 bg-error/10 px-4 py-2.5 text-sm text-error"
              >
                <span className="min-w-0 break-words">{error}</span>
                <button
                  type="button"
                  onClick={() => setError(null)}
                  aria-label="关闭错误提示"
                  className="shrink-0 rounded p-0.5 hover:bg-error/15"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            )}
            {(credits === 0 || creditBlocked) && (
              <div
                data-testid="credits-depleted-banner"
                className="mb-4 flex items-center justify-between gap-3 rounded-md border border-warning/30 bg-warning/10 px-4 py-2.5 text-sm text-warning"
              >
                <span>
                  {creditBlocked
                    ? '额度不足，本次生成已被拦截。前往计费页切换套餐即可补充额度（演示环境）。'
                    : '额度为 0：新的生成会被拦截。前往计费页切换套餐即可补充额度（演示环境）。'}
                </span>
                <a href="/billing" className="shrink-0 font-medium underline hover:text-content-primary">
                  前往计费页
                </a>
              </div>
            )}
            {isPlanning && (
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 h-[calc(100dvh-3.5rem-2.5rem)] overflow-hidden">
                <div className="lg:col-span-5 flex flex-col gap-4 min-h-0">
                  <div className="flex items-center justify-between">
                    <WorkflowStatusBar currentStep={project.agent_state?.step} />
                    <AutonomySelector
                      value={project.agent_state?.autonomy_level || 'confirm_each'}
                      onChange={(level) =>
                        handleWizardStateChange({
                          ...(project.agent_state || {}),
                          autonomy_level: level,
                        } as NonNullable<Project['agent_state']>)
                      }
                    />
                  </div>
                  <AgentChat
                    projectId={project.id}
                    mode="vibe"
                    agentState={project.agent_state}
                    initialPrompt={initialPrompt}
                    sourceUrl={project.source_url}
                    onStatusChange={(s) => setProject((prev) => (prev ? { ...prev, status: s } : null))}
                    onAgentStateChange={(next) =>
                      setProject((prev) =>
                        prev ? { ...prev, agent_state: { ...(prev.agent_state || {}), ...next } } : null
                      )
                    }
                  />
                </div>
                <div className="lg:col-span-7 min-h-0 overflow-y-auto">
                  <AgentCanvas agentState={project.agent_state} />
                </div>
              </div>
            )}

            {isGenerating && (
              <div className="max-w-2xl mx-auto h-full flex flex-col items-center justify-center overflow-y-auto py-4">
                <GenerationPanel
                  project={project}
                  latestJob={latestJob}
                  steps={PIPELINE_STEPS}
                  currentStepIndex={currentStepIndex}
                  currentDescription={pipelineDescription[project.status]}
                />
              </div>
            )}

            {!isPlanning && !isGenerating && (
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 h-auto lg:h-[calc(100dvh-3.5rem-2.5rem)] overflow-y-auto">
                {/* Left: Agent + Scenes */}
                <div className="lg:col-span-3 flex flex-col gap-4 min-h-0 min-w-0">
                  <AgentChat
                    projectId={project.id}
                    size="sm"
                    mode="modify"
                    agentState={project.agent_state}
                    initialPrompt={initialPrompt}
                    sourceUrl={project.source_url}
                    onStatusChange={(s) => {
                      setProject((prev) => (prev ? { ...prev, status: s } : null));
                      if (s === 'generating') {
                        setTimeout(() => refreshProject(), 500);
                      }
                    }}
                    selectedSceneId={selectedSceneId}
                    scenes={scenes}
                  />
                  <SceneCards
                    scenes={scenes}
                    selectedId={selectedSceneId}
                    onSelect={setSelectedSceneId}
                  />
                </div>

                {/* Center: Preview + Pipeline */}
                <div className="lg:col-span-6 flex flex-col gap-4 min-h-0 min-w-0 min-h-[360px]">
                  <div className="flex-1 bg-black rounded-lg overflow-hidden min-h-0">
                    {latestJob?.output_url || latestJob?.html_output_url ? (
                      <PreviewPlayer
                        outputUrl={toSameOriginUrl(latestJob?.output_url)}
                        htmlOutputUrl={toSameOriginUrl(latestJob?.html_output_url)}
                        format={previewFormat}
                        isPlaceholder={
                          !!latestJob?.output_url && latestJob.output_url.includes('/sample.mp4')
                        }
                      />
                    ) : (
                      <div className="w-full h-full flex flex-col items-center justify-center text-content-tertiary bg-background-surface border border-border-subtle rounded-lg">
                        <Film className="w-12 h-12 mb-3 text-content-tertiary/50" />
                        <p className="text-sm font-medium text-content-secondary">视频生成后会在这里预览</p>
                        <p className="text-xs mt-1">在左侧 Agent 面板输入指令开始生成或修改</p>
                      </div>
                    )}
                  </div>
                  {latestJob && !isGenerating && (
                    <div className="flex justify-end gap-2">
                      <Link
                        href={`/projects/${project.id}/editor`}
                        className="focus-ring inline-flex items-center justify-center rounded-md font-medium transition-all duration-150 ease-out bg-background-elevated border border-border text-content-primary hover:bg-background-hover px-3 py-1.5 text-sm"
                      >
                        <Scissors className="w-4 h-4 mr-1.5" />
                        时间线编辑器
                      </Link>
                      <Button variant="secondary" size="sm" onClick={handleRerender} disabled={rerendering}>
                        <RefreshCw className={`w-4 h-4 mr-1.5 ${rerendering ? 'animate-spin' : ''}`} />
                        {rerendering ? '重新渲染中…' : '用当前时间线重新渲染'}
                      </Button>
                    </div>
                  )}
                  {(project.status === 'ready' || project.status === 'failed') && (
                    <div className="bg-background-surface border border-border-subtle rounded-lg p-4">
                      <Pipeline
                        steps={PIPELINE_STEPS}
                        currentStepIndex={currentStepIndex}
                        currentDescription={pipelineDescription[project.status]}
                      />
                    </div>
                  )}
                  {project.status === 'failed' && (
                    <div className="bg-error/10 border border-error/20 rounded-lg p-4 text-sm text-error">
                      <p className="font-medium">生成失败</p>
                      <p className="mt-1">{latestJob?.error_message || '渲染过程中出现错误，请尝试重新生成。'}</p>
                    </div>
                  )}
                </div>

                {/* Right: Properties */}
                <div className="lg:col-span-3 min-h-0 min-w-0">
                  <PropertyPanel
                    project={project}
                    selectedScene={scenes.find((s) => s.id === selectedSceneId)}
                    assets={assets}
                    onChange={handlePropertyChange}
                    onSceneApply={handleSceneApply}
                    onProjectSave={handleProjectSave}
                    onUpload={() => window.open(`/projects/${project.id}/assets`, '_blank')}
                    applying={applyingScene}
                    saving={savingProject}
                  />
                </div>
              </div>
            )}
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}
