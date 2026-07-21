'use client';

import { AgentState } from '@/lib/types';

export function AgentCanvas({ agentState }: { agentState?: AgentState }) {
  const step = (agentState?.step || 'understand') as string;
  const payload = (agentState?.payload || {}) as Record<string, any>;

  // Vibe sessions store artifacts under payload.*, but planning projects created
  // by the legacy agent keep script/assets/scenes/effects at the top level of
  // agent_state. Fall back to top-level keys for backward compatibility.
  const script = payload.script ?? agentState?.script;
  const assets = payload.assets ?? agentState?.assets;
  const scenes = payload.scenes ?? agentState?.scenes;
  const effects = payload.effects ?? agentState?.effects;

  if (step === 'understand') {
    const u = payload.understand;
    return (
      <div className="bg-background-surface border border-border-subtle rounded-lg p-5">
        <h3 className="text-sm font-semibold text-content-secondary mb-3">需求理解</h3>
        <p className="text-content-primary text-lg mb-4">{u?.summary || '等待输入…'}</p>
        <div className="flex flex-wrap gap-2 text-xs">
          {u?.format && <span className="px-2 py-1 rounded-full bg-background-elevated border border-border-subtle">{u.format}</span>}
          {u?.duration && <span className="px-2 py-1 rounded-full bg-background-elevated border border-border-subtle">{u.duration} 秒</span>}
          {u?.audience && <span className="px-2 py-1 rounded-full bg-background-elevated border border-border-subtle">{u.audience}</span>}
          {u?.style && <span className="px-2 py-1 rounded-full bg-background-elevated border border-border-subtle">{u.style}</span>}
        </div>
      </div>
    );
  }

  if (step === 'script') {
    const s = script;
    return (
      <div className="bg-background-surface border border-border-subtle rounded-lg p-5">
        <h3 className="text-sm font-semibold text-content-secondary mb-3">脚本</h3>
        <h4 className="text-xl font-bold text-content-primary mb-2">{s?.title || '未命名'}</h4>
        <p className="text-brand-400 mb-4">{s?.hook || ''}</p>
        <p className="text-content-secondary text-sm whitespace-pre-line">{s?.narrative_arc || ''}</p>
      </div>
    );
  }

  if (step === 'assets') {
    const needed: any[] = assets?.needed || [];
    return (
      <div className="bg-background-surface border border-border-subtle rounded-lg p-5">
        <h3 className="text-sm font-semibold text-content-secondary mb-3">素材清单</h3>
        {needed.length === 0 ? (
          <p className="text-content-tertiary">暂无素材需求</p>
        ) : (
          <ul className="space-y-2">
            {needed.map((item, idx) => (
              <li
                key={idx}
                className="text-sm text-content-secondary bg-background-elevated/40 rounded border border-border-subtle/50 px-3 py-2"
              >
                <span className="font-medium text-content-primary">{item.description || '未命名素材'}</span>
                {item.source && <span className="ml-2 text-xs text-content-tertiary">({item.source})</span>}
              </li>
            ))}
          </ul>
        )}
      </div>
    );
  }

  if (step === 'scenes') {
    const sceneList: any[] = scenes?.scenes || [];
    return (
      <div className="bg-background-surface border border-border-subtle rounded-lg p-5">
        <h3 className="text-sm font-semibold text-content-secondary mb-3">场景规划</h3>
        {sceneList.length === 0 ? (
          <p className="text-content-tertiary">暂无场景</p>
        ) : (
          <div className="space-y-3">
            {sceneList.map((scene, idx) => (
              <div
                key={idx}
                className="text-sm text-content-secondary bg-background-elevated/40 rounded border border-border-subtle/50 p-3"
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-medium text-content-primary">场景 {idx + 1}</span>
                  <span className="text-xs text-content-tertiary">
                    {scene.start != null ? `${scene.start}s` : scene.start_time != null ? `${scene.start_time}s` : ''}
                    {scene.duration != null ? ` · ${scene.duration} 秒` : ''}
                  </span>
                </div>
                <p className="mb-1">{scene.description || scene.text || '无描述'}</p>
                {scene.visual && <p className="text-xs text-content-tertiary">画面：{scene.visual}</p>}
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  if (step === 'effects') {
    const effectList: any[] = effects?.effects || [];
    return (
      <div className="bg-background-surface border border-border-subtle rounded-lg p-5">
        <h3 className="text-sm font-semibold text-content-secondary mb-3">动效设计</h3>
        {effectList.length === 0 ? (
          <p className="text-content-tertiary">暂无动效设计</p>
        ) : (
          <div className="space-y-3">
            {effectList.map((effect, idx) => (
              <div
                key={idx}
                className="text-sm text-content-secondary bg-background-elevated/40 rounded border border-border-subtle/50 p-3"
              >
                <p className="font-medium text-content-primary mb-1">
                  场景 {effect.scene_index != null ? effect.scene_index + 1 : idx + 1}
                </p>
                {effect.visual_style && <p>风格：{effect.visual_style}</p>}
                {effect.animation_keywords && effect.animation_keywords.length > 0 && (
                  <p className="text-xs text-content-tertiary mt-1">
                    关键词：{effect.animation_keywords.join('、')}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  if (step === 'render' || step === 'done' || step === 'approved' || step === 'generating') {
    const render = payload.render;
    return (
      <div className="bg-background-surface border border-border-subtle rounded-lg p-5">
        <h3 className="text-sm font-semibold text-content-secondary mb-3">渲染</h3>
        <p className="text-content-primary">
          {render?.job_id ? `渲染任务已创建：${render.job_id}` : '正在准备渲染…'}
        </p>
      </div>
    );
  }

  return (
    <div className="bg-background-surface border border-border-subtle rounded-lg p-5 text-content-tertiary">
      当前步骤：{step}
    </div>
  );
}
