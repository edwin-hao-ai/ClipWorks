'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { AuthGuard } from '@/components/layout/AuthGuard';
import { AgentChat } from '@/components/project/AgentChat';
import { SceneCards } from '@/components/project/SceneCards';
import { PreviewPlayer } from '@/components/project/PreviewPlayer';
import { PropertyPanel } from '@/components/project/PropertyPanel';
import { Pipeline } from '@/components/project/Pipeline';
import { Button } from '@/components/ui/Button';
import { Project, Scene } from '@/lib/types';
import { api } from '@/lib/api';
import { Sparkles } from 'lucide-react';
import { getDemoProjectById } from '@/lib/demoData';

const PIPELINE_STEPS = [
  { id: 'understand', label: '理解需求' },
  { id: 'analyze', label: '分析素材' },
  { id: 'script', label: '编写脚本' },
  { id: 'scenes', label: '生成场景' },
  { id: 'render', label: '渲染成片' },
  { id: 'output', label: '输出成片' },
];

export default function ProjectWorkspacePage() {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [selectedSceneId, setSelectedSceneId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [generationError, setGenerationError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await api.get(`/projects/${id}`);
        if (!cancelled) {
          setProject(data);
          if (data.composition?.metadata?.scenes) {
            setScenes(data.composition.metadata.scenes);
          }
        }
      } catch (err) {
        if (!cancelled) {
          const demo = getDemoProjectById(id);
          if (demo) setProject(demo);
          else setError(err instanceof Error ? err.message : '加载项目失败');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, [id]);

  if (loading) {
    return (
      <AuthGuard>
        <div className="min-h-screen flex items-center justify-center bg-background-base text-content-secondary">
          <div className="flex flex-col items-center gap-4">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500" />
            <p className="text-sm">加载项目中…</p>
          </div>
        </div>
      </AuthGuard>
    );
  }

  if (error || !project) {
    return (
      <AuthGuard>
        <div className="min-h-screen flex items-center justify-center bg-background-base">
          <div className="text-center max-w-md">
            <p className="text-error mb-4">{error || '项目不存在'}</p>
            <Button onClick={() => window.location.reload()}>重试</Button>
          </div>
        </div>
      </AuthGuard>
    );
  }

  const currentStepIndex = project.status === 'draft' ? -1 : project.status === 'generating' ? 3 : 5;

  return (
    <AuthGuard>
      <div className="flex min-h-screen bg-background-base">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <TopBar
            title={project.title}
            showBack
            backHref="/projects"
            right={
              <>
                <Button variant="secondary" size="sm">导出 HTML</Button>
                <Button size="sm">导出 MP4</Button>
              </>
            }
          />
          <main className="flex-1 p-5 overflow-auto lg:overflow-hidden">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 h-auto lg:h-[calc(100vh-3.5rem-2.5rem)]">
              {/* Left: Agent + Scenes */}
              <div className="lg:col-span-3 flex flex-col gap-4 min-h-0">
                {project.status === 'draft' && (
                  <div className="space-y-2">
                    <Button
                      onClick={async () => {
                        setIsGenerating(true);
                        setGenerationError(null);
                        try {
                          await api.post(`/projects/${project.id}/renders/agent-generate`, { prompt: project.title });
                          setProject({ ...project, status: 'generating' });
                        } catch (err) {
                          setGenerationError(err instanceof Error ? err.message : '生成失败，请重试');
                        } finally {
                          setIsGenerating(false);
                        }
                      }}
                      disabled={isGenerating}
                      className="w-full"
                    >
                      {isGenerating ? (
                        <span className="flex items-center justify-center gap-2">
                          <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                          生成中…
                        </span>
                      ) : (
                        <span className="flex items-center gap-2">
                          <Sparkles className="w-4 h-4" />
                          开始生成视频
                        </span>
                      )}
                    </Button>
                    {generationError && (
                      <p className="text-sm text-error text-center">{generationError}</p>
                    )}
                  </div>
                )}
                <AgentChat
                  projectId={project.id}
                  onStatusChange={(s) => setProject({ ...project, status: s })}
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
              <div className="lg:col-span-6 flex flex-col gap-4 min-h-0 min-h-[360px]">
                <div className="flex-1 bg-black rounded-lg overflow-hidden min-h-0">
                  <PreviewPlayer videoUrl={project.latest_output_url} />
                </div>
                {project.status === 'generating' && (
                  <div className="bg-background-surface border border-border-subtle rounded-lg p-4">
                    <Pipeline
                      steps={PIPELINE_STEPS}
                      currentStepIndex={currentStepIndex}
                      currentDescription="正在生成场景 2/4：解决方案展示"
                    />
                  </div>
                )}
              </div>

              {/* Right: Properties */}
              <div className="lg:col-span-3 min-h-0">
                <PropertyPanel
                  project={project}
                  selectedScene={scenes.find((s) => s.id === selectedSceneId)}
                />
              </div>
            </div>
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}
