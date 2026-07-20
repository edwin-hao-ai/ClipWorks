'use client';

import { AgentAssetItem, AgentAssetPlan } from '@/lib/types';
import { Button } from '@/components/ui/Button';
import { Plus, Trash2 } from 'lucide-react';

const ASSET_TYPES: { value: AgentAssetItem['type']; label: string }[] = [
  { value: 'image', label: '搜索图片' },
  { value: 'generated_image', label: '生成图' },
  { value: 'video', label: '视频' },
  { value: 'music', label: '音乐' },
];

export interface AssetsPanelProps {
  value?: AgentAssetPlan | null;
  onChange: (assets: AgentAssetPlan) => void;
}

export function AssetsPanel({ value, onChange }: AssetsPanelProps) {
  const assets = value || { needed: [] };

  const updateItem = (idx: number, patch: Partial<AgentAssetItem>) => {
    const needed = assets.needed.map((item, i) => (i === idx ? { ...item, ...patch } : item));
    onChange({ ...assets, needed });
  };

  const addItem = () => {
    onChange({
      ...assets,
      needed: [...assets.needed, { type: 'image', description: '', query: '', count: 1 }],
    });
  };

  const removeItem = (idx: number) => {
    const needed = assets.needed.filter((_, i) => i !== idx);
    onChange({ ...assets, needed });
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-content-primary">素材</h2>
        <Button size="sm" onClick={addItem}>
          <Plus className="w-4 h-4 mr-1" /> 添加素材
        </Button>
      </div>
      <div className="space-y-3">
        {assets.needed.map((item, idx) => (
          <div key={idx} className="grid grid-cols-12 gap-3 items-end bg-background-elevated p-3 rounded-md">
            <div className="col-span-2 space-y-1">
              <label htmlFor={`asset-type-${idx}`} className="text-xs text-content-secondary">类型</label>
              <select
                id={`asset-type-${idx}`}
                value={item.type}
                onChange={(e) => updateItem(idx, { type: e.target.value as AgentAssetItem['type'] })}
                className="w-full rounded-md bg-background-base border border-border px-2 py-1.5 text-sm text-content-primary focus-ring"
              >
                {ASSET_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="col-span-4 space-y-1">
              <label htmlFor={`asset-desc-${idx}`} className="text-xs text-content-secondary">描述</label>
              <input
                id={`asset-desc-${idx}`}
                type="text"
                value={item.description}
                onChange={(e) => updateItem(idx, { description: e.target.value })}
                className="w-full rounded-md bg-background-base border border-border px-2 py-1.5 text-sm text-content-primary focus-ring"
              />
            </div>
            <div className="col-span-4 space-y-1">
              <label htmlFor={`asset-query-${idx}`} className="text-xs text-content-secondary">检索词 / Prompt</label>
              <input
                id={`asset-query-${idx}`}
                type="text"
                value={item.query}
                onChange={(e) => updateItem(idx, { query: e.target.value })}
                className="w-full rounded-md bg-background-base border border-border px-2 py-1.5 text-sm text-content-primary focus-ring"
              />
            </div>
            <div className="col-span-1 space-y-1">
              <label htmlFor={`asset-count-${idx}`} className="text-xs text-content-secondary">数量</label>
              <input
                id={`asset-count-${idx}`}
                type="number"
                min={1}
                value={item.count}
                onChange={(e) => updateItem(idx, { count: Number(e.target.value) })}
                className="w-full rounded-md bg-background-base border border-border px-2 py-1.5 text-sm text-content-primary focus-ring"
              />
            </div>
            <div className="col-span-1">
              <button
                type="button"
                onClick={() => removeItem(idx)}
                className="p-2 text-content-secondary hover:text-error focus-ring"
                aria-label="删除素材"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          </div>
        ))}
        {assets.needed.length === 0 && (
          <p className="text-sm text-content-tertiary">暂无素材，点击上方按钮添加。</p>
        )}
      </div>
    </div>
  );
}
