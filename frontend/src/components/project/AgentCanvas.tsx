'use client';

import {
  AgentState,
  Project,
  AgentUnderstandPayload,
  AgentScriptPayload,
  AgentAssetsPayload,
  AgentScenesPayload,
  AgentEffectsPayload,
} from '@/lib/types';
import { VideoPreview } from './VideoPreview';
import {
  Lightbulb,
  FileText,
  Images,
  Clapperboard,
  Sparkles,
  Film,
} from 'lucide-react';

export interface AgentCanvasProps {
  agentState?: AgentState;
  project?: Project;
}

const STEP_TITLES: Record<string, string> = {
  understand: '需求理解',
  script: '脚本',
  assets: '素材清单',
  scenes: '分镜',
  effects: '动效',
  render: '渲染与预览',
};

function Card({
  title,
  icon: Icon,
  children,
}: {
  title: string;
  icon: React.ComponentType<{ className?: string }>;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-background-surface border border-border-subtle rounded-lg p-5 h-full">
      <div className="flex items-center gap-2 mb-4">
        <Icon className="w-4 h-4 text-brand-400" />
        <h3 className="text-sm font-semibold text-content-secondary">{title}</h3>
      </div>
      {children}
    </div>
  );
}

function MetaChip({ children }: { children: React.ReactNode }) {
  return (
    <span className="px-2.5 py-1 rounded-full text-xs bg-background-elevated border border-border-subtle text-content-secondary">
      {children}
    </span>
  );
}

function EmptyState({ children }: { children: React.ReactNode }) {
  return <p className="text-sm text-content-tertiary">{children}</p>;
}

function UnderstandArtifact({ payload }: { payload?: AgentUnderstandPayload }) {
  const u = payload || {};
  const chips = [
    u.format,
    u.duration != null ? `${u.duration} 秒` : null,
    u.audience,
    u.style,
    u.platform,
    u.cta,
  ].filter(Boolean);

  return (
    <Card title={STEP_TITLES.understand} icon={Lightbulb}>
      <p className="text-content-primary text-lg mb-4">
        {u.summary || '等待输入…'}
      </p>
      {chips.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {chips.map((text, idx) => (
            <MetaChip key={idx}>{text}</MetaChip>
          ))}
        </div>
      )}
    </Card>
  );
}

function ScriptArtifact({
  payload,
  fullScript,
}: {
  payload?: AgentScriptPayload;
  fullScript?: AgentState['script'];
}) {
  const s = payload || {};
  const roles = fullScript?.roles || [];

  return (
    <Card title={STEP_TITLES.script} icon={FileText}>
      <h4 className="text-xl font-bold text-content-primary mb-2">
        {s.title || fullScript?.title || '未命名'}
      </h4>
      {(s.hook || fullScript?.hook) && (
        <p className="text-brand-400 mb-4">{s.hook || fullScript?.hook}</p>
      )}
      {roles.length > 0 && (
        <div className="mb-4 flex flex-wrap gap-2">
          {roles.map((role, idx) => (
            <MetaChip key={idx}>
              {role.name} · {role.perspective}
            </MetaChip>
          ))}
        </div>
      )}
      {(s.narrative_arc || fullScript?.narrative_arc) && (
        <p className="text-content-secondary text-sm whitespace-pre-line mb-4">
          {s.narrative_arc || fullScript?.narrative_arc}
        </p>
      )}
      {(s.cta || fullScript?.cta) && (
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-md bg-brand-500/10 border border-brand-500/30 text-brand-400 text-sm">
          CTA：{s.cta || fullScript?.cta}
        </div>
      )}
    </Card>
  );
}

function AssetsArtifact({ payload }: { payload?: AgentAssetsPayload }) {
  const needed = payload?.needed || [];

  return (
    <Card title={STEP_TITLES.assets} icon={Images}>
      {needed.length === 0 ? (
        <EmptyState>暂无素材需求。</EmptyState>
      ) : (
        <ul className="space-y-2">
          {needed.map((item, idx) => (
            <li
              key={idx}
              className="flex items-center justify-between px-3 py-2 rounded-md bg-background-elevated border border-border-subtle"
            >
              <span className="text-sm text-content-primary">
                {item.description || '未命名素材'}
              </span>
              {item.source && (
                <span className="text-xs text-content-tertiary capitalize">
                  {item.source}
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  if (m > 0) return `${m}:${s.toString().padStart(2, '0')}`;
  return `${s}s`;
}

function ScenesArtifact({ payload }: { payload?: AgentScenesPayload }) {
  const scenes = payload?.scenes || [];

  return (
    <Card title={STEP_TITLES.scenes} icon={Clapperboard}>
      {scenes.length === 0 ? (
        <EmptyState>暂无分镜。</EmptyState>
      ) : (
        <ol className="space-y-3">
          {scenes.map((scene, idx) => (
            <li
              key={scene.id ?? idx}
              className="flex gap-3 px-3 py-3 rounded-md bg-background-elevated border border-border-subtle"
            >
              <div className="flex flex-col items-center justify-center min-w-[3.5rem] text-xs text-content-tertiary">
                <span>{formatTime(scene.start_time)}</span>
                <span className="w-8 h-px bg-border-subtle my-1" />
                <span>{formatTime(scene.duration)}</span>
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-content-primary truncate">
                  {scene.name || `场景 ${idx + 1}`}
                </div>
                {scene.description && (
                  <p className="text-xs text-content-secondary mt-0.5 line-clamp-2">
                    {scene.description}
                  </p>
                )}
              </div>
            </li>
          ))}
        </ol>
      )}
    </Card>
  );
}

function EffectsArtifact({ payload }: { payload?: AgentEffectsPayload }) {
  const effects = payload?.effects || [];

  return (
    <Card title={STEP_TITLES.effects} icon={Sparkles}>
      {effects.length === 0 ? (
        <EmptyState>暂无动效规划。</EmptyState>
      ) : (
        <div className="space-y-3">
          {effects.map((effect, idx) => (
            <div
              key={idx}
              className="px-3 py-3 rounded-md bg-background-elevated border border-border-subtle"
            >
              <div className="text-sm font-medium text-content-primary mb-1">
                场景 {effect.scene_index ?? idx + 1}
                {effect.visual_style && (
                  <span className="ml-2 text-xs text-brand-400">
                    {effect.visual_style}
                  </span>
                )}
              </div>
              {effect.animation_keywords && effect.animation_keywords.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {effect.animation_keywords.map((kw, kidx) => (
                    <MetaChip key={kidx}>{kw}</MetaChip>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </Card>
  );
}

function RenderArtifact({ project }: { project?: Project }) {
  const outputUrl = project?.latest_output_url || null;
  const isPlaceholder = false;

  return (
    <Card title={STEP_TITLES.render} icon={Film}>
      {outputUrl ? (
        <div className="h-64">
          <VideoPreview outputUrl={outputUrl} htmlOutputUrl={null} isPlaceholder={isPlaceholder} />
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <Film className="w-10 h-10 text-content-tertiary mb-3" />
          <p className="text-sm text-content-secondary">等待渲染完成…</p>
          <p className="text-xs text-content-tertiary mt-1">
            渲染完成后将在此显示成片预览。
          </p>
        </div>
      )}
    </Card>
  );
}

export function AgentCanvas({ agentState, project }: AgentCanvasProps) {
  const step = agentState?.step || 'understand';
  const payload = agentState?.payload || {};

  switch (step) {
    case 'understand':
      return <UnderstandArtifact payload={payload.understand} />;
    case 'script':
      return <ScriptArtifact payload={payload.script} fullScript={agentState?.script} />;
    case 'assets':
      return <AssetsArtifact payload={payload.assets} />;
    case 'scenes':
      return <ScenesArtifact payload={payload.scenes} />;
    case 'effects':
      return <EffectsArtifact payload={payload.effects} />;
    case 'render':
      return <RenderArtifact project={project} />;
    default:
      return (
        <Card title="当前步骤" icon={Lightbulb}>
          <p className="text-content-tertiary">当前步骤：{step}</p>
        </Card>
      );
  }
}
