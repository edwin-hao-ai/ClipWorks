'use client';

import { AgentEffectItem, AgentEffectPlan, AgentScenePlan } from '@/lib/types';

const STYLE_PRESETS = ['深蓝科技粒子', '暖橙光晕', '极简高级', '赛博霓虹', '清新自然'];

export interface EffectsPanelProps {
  value?: AgentEffectPlan | null;
  scenes?: AgentScenePlan | null;
  onChange: (effects: AgentEffectPlan) => void;
}

export function EffectsPanel({ value, scenes, onChange }: EffectsPanelProps) {
  const effects = value || { effects: [] };
  const sceneList = scenes?.scenes || [];

  const ensureEffects = (): AgentEffectPlan => {
    if (effects.effects.length >= sceneList.length) return effects;
    const generated = sceneList.map((_, idx) => ({
      scene_index: idx,
      visual_style: '',
      animation_keywords: [],
      generate_image: false,
      generate_image_prompt: '',
    }));
    return { effects: generated };
  };

  const working = ensureEffects();

  const updateEffect = (idx: number, patch: Partial<AgentEffectItem>) => {
    const list = working.effects.map((e, i) => (i === idx ? { ...e, ...patch } : e));
    onChange({ effects: list });
  };

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-content-primary">动效</h2>
      <div className="space-y-4">
        {sceneList.map((scene, idx) => {
          const effect = working.effects[idx] || {
            scene_index: idx,
            visual_style: '',
            animation_keywords: [],
            generate_image: false,
            generate_image_prompt: '',
          };
          return (
            <div key={idx} className="bg-background-elevated p-3 rounded-md space-y-3">
              <div className="text-sm font-medium text-content-secondary">
                场景 {idx + 1}：{scene.text || scene.description || '未命名'}
              </div>
              <div className="flex flex-wrap gap-2">
                {STYLE_PRESETS.map((style) => (
                  <button
                    key={style}
                    type="button"
                    onClick={() => updateEffect(idx, { visual_style: style })}
                    className={`px-2 py-1 rounded-full text-xs border focus-ring ${
                      effect.visual_style === style
                        ? 'bg-brand-500/20 border-brand-500 text-brand-400'
                        : 'border-border text-content-secondary hover:bg-background-hover'
                    }`}
                  >
                    {style}
                  </button>
                ))}
              </div>
              <div className="space-y-1">
                <label htmlFor={`effect-style-${idx}`} className="text-xs text-content-secondary">视觉风格</label>
                <input
                  id={`effect-style-${idx}`}
                  type="text"
                  value={effect.visual_style}
                  onChange={(e) => updateEffect(idx, { visual_style: e.target.value })}
                  className="w-full rounded-md bg-background-base border border-border px-2 py-1.5 text-sm text-content-primary focus-ring"
                />
              </div>
              <div className="space-y-1">
                <label htmlFor={`effect-keywords-${idx}`} className="text-xs text-content-secondary">动画关键词（逗号分隔）</label>
                <input
                  id={`effect-keywords-${idx}`}
                  type="text"
                  value={effect.animation_keywords.join('，')}
                  onChange={(e) =>
                    updateEffect(idx, {
                      animation_keywords: e.target.value.split(/[,，]/).map((s) => s.trim()).filter(Boolean),
                    })
                  }
                  className="w-full rounded-md bg-background-base border border-border px-2 py-1.5 text-sm text-content-primary focus-ring"
                />
              </div>
              <label htmlFor={`effect-generate-${idx}`} className="flex items-center gap-2 text-sm text-content-primary">
                <input
                  id={`effect-generate-${idx}`}
                  type="checkbox"
                  checked={effect.generate_image}
                  onChange={(e) => updateEffect(idx, { generate_image: e.target.checked })}
                  className="rounded border-border focus-ring"
                />
                需要生成图
              </label>
              {effect.generate_image && (
                <div className="space-y-1">
                  <label htmlFor={`effect-prompt-${idx}`} className="text-xs text-content-secondary">生成图 Prompt（英文）</label>
                  <input
                    id={`effect-prompt-${idx}`}
                    type="text"
                    value={effect.generate_image_prompt}
                    onChange={(e) => updateEffect(idx, { generate_image_prompt: e.target.value })}
                    className="w-full rounded-md bg-background-base border border-border px-2 py-1.5 text-sm text-content-primary focus-ring"
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
