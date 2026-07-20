'use client';

import { AgentSceneItem, AgentScenePlan } from '@/lib/types';
import { Button } from '@/components/ui/Button';
import { Plus, Trash2 } from 'lucide-react';

export interface ScenesPanelProps {
  value?: AgentScenePlan | null;
  onChange: (scenes: AgentScenePlan) => void;
}

export function ScenesPanel({ value, onChange }: ScenesPanelProps) {
  const scenes = value || { scenes: [] };

  const updateItem = (idx: number, patch: Partial<AgentSceneItem>) => {
    const list = scenes.scenes.map((s, i) => (i === idx ? { ...s, ...patch } : s));
    onChange({ ...scenes, scenes: list });
  };

  const addScene = () => {
    const start = Math.max(0, ...scenes.scenes.map((s) => s.start + s.duration));
    onChange({
      ...scenes,
      scenes: [
        ...scenes.scenes,
        {
          start,
          duration: 5,
          description: '',
          visual: '',
          text: '',
          visual_type: 'text',
          shot: '',
          transition: 'fade',
          lower_third: '',
          required_assets: [],
        },
      ],
    });
  };

  const removeScene = (idx: number) => {
    onChange({ ...scenes, scenes: scenes.scenes.filter((_, i) => i !== idx) });
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-content-primary">场景</h2>
        <Button size="sm" onClick={addScene}>
          <Plus className="w-4 h-4 mr-1" /> 添加场景
        </Button>
      </div>
      <div className="space-y-3">
        {scenes.scenes.map((scene, idx) => (
          <div key={idx} className="bg-background-elevated p-3 rounded-md space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-content-secondary">场景 {idx + 1}</span>
              <button
                type="button"
                onClick={() => removeScene(idx)}
                className="p-1.5 text-content-secondary hover:text-error focus-ring"
                aria-label="删除场景"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
            <div className="grid grid-cols-12 gap-3">
              <div className="col-span-2 space-y-1">
                <label htmlFor={`scene-start-${idx}`} className="text-xs text-content-secondary">开始</label>
                <input
                  id={`scene-start-${idx}`}
                  type="number"
                  value={scene.start}
                  onChange={(e) => updateItem(idx, { start: Number(e.target.value) })}
                  className="w-full rounded-md bg-background-base border border-border px-2 py-1.5 text-sm text-content-primary focus-ring"
                />
              </div>
              <div className="col-span-2 space-y-1">
                <label htmlFor={`scene-duration-${idx}`} className="text-xs text-content-secondary">时长</label>
                <input
                  id={`scene-duration-${idx}`}
                  type="number"
                  value={scene.duration}
                  onChange={(e) => updateItem(idx, { duration: Number(e.target.value) })}
                  className="w-full rounded-md bg-background-base border border-border px-2 py-1.5 text-sm text-content-primary focus-ring"
                />
              </div>
              <div className="col-span-2 space-y-1">
                <label htmlFor={`scene-transition-${idx}`} className="text-xs text-content-secondary">转场</label>
                <select
                  id={`scene-transition-${idx}`}
                  value={scene.transition}
                  onChange={(e) => updateItem(idx, { transition: e.target.value })}
                  className="w-full rounded-md bg-background-base border border-border px-2 py-1.5 text-sm text-content-primary focus-ring"
                >
                  <option value="fade">fade</option>
                  <option value="slide">slide</option>
                  <option value="zoom">zoom</option>
                </select>
              </div>
              <div className="col-span-3 space-y-1">
                <label htmlFor={`scene-shot-${idx}`} className="text-xs text-content-secondary">镜头</label>
                <input
                  id={`scene-shot-${idx}`}
                  type="text"
                  value={scene.shot}
                  onChange={(e) => updateItem(idx, { shot: e.target.value })}
                  className="w-full rounded-md bg-background-base border border-border px-2 py-1.5 text-sm text-content-primary focus-ring"
                />
              </div>
              <div className="col-span-3 space-y-1">
                <label htmlFor={`scene-type-${idx}`} className="text-xs text-content-secondary">类型</label>
                <select
                  id={`scene-type-${idx}`}
                  value={scene.visual_type}
                  onChange={(e) => updateItem(idx, { visual_type: e.target.value as AgentSceneItem['visual_type'] })}
                  className="w-full rounded-md bg-background-base border border-border px-2 py-1.5 text-sm text-content-primary focus-ring"
                >
                  <option value="product">product</option>
                  <option value="broll">broll</option>
                  <option value="metaphor">metaphor</option>
                  <option value="text">text</option>
                </select>
              </div>
            </div>
            <div className="space-y-1">
              <label htmlFor={`scene-visual-${idx}`} className="text-xs text-content-secondary">画面描述</label>
              <input
                id={`scene-visual-${idx}`}
                type="text"
                value={scene.visual}
                onChange={(e) => updateItem(idx, { visual: e.target.value })}
                className="w-full rounded-md bg-background-base border border-border px-2 py-1.5 text-sm text-content-primary focus-ring"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1">
                <label htmlFor={`scene-text-${idx}`} className="text-xs text-content-secondary">文案</label>
                <input
                  id={`scene-text-${idx}`}
                  type="text"
                  value={scene.text}
                  onChange={(e) => updateItem(idx, { text: e.target.value })}
                  className="w-full rounded-md bg-background-base border border-border px-2 py-1.5 text-sm text-content-primary focus-ring"
                />
              </div>
              <div className="space-y-1">
                <label htmlFor={`scene-lower-third-${idx}`} className="text-xs text-content-secondary">角标</label>
                <input
                  id={`scene-lower-third-${idx}`}
                  type="text"
                  value={scene.lower_third}
                  onChange={(e) => updateItem(idx, { lower_third: e.target.value })}
                  className="w-full rounded-md bg-background-base border border-border px-2 py-1.5 text-sm text-content-primary focus-ring"
                />
              </div>
            </div>
          </div>
        ))}
        {scenes.scenes.length === 0 && (
          <p className="text-sm text-content-tertiary">暂无场景，点击上方按钮添加。</p>
        )}
      </div>
    </div>
  );
}
