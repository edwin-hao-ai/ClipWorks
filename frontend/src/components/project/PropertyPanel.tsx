'use client';

import { Project, Scene } from '@/lib/types';
import { clsx } from 'clsx';
import { Type, Clock, Monitor, Image, Music } from 'lucide-react';

interface PropertyPanelProps {
  project: Project;
  selectedScene?: Scene;
}

export function PropertyPanel({ project, selectedScene }: PropertyPanelProps) {
  return (
    <div className="bg-background-surface border border-border-subtle rounded-lg p-4 h-full overflow-y-auto">
      {selectedScene ? (
        <div className="space-y-5">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <Type className="w-4 h-4 text-brand-400" />
            场景属性
          </div>
          <div>
            <label className="text-xs text-content-secondary block mb-1">场景名称</label>
            <input
              type="text"
              defaultValue={selectedScene.name}
              className="w-full bg-background-elevated border border-border-subtle rounded-md px-2 py-1.5 text-sm outline-none focus:border-brand-500"
            />
          </div>
          <div>
            <label className="text-xs text-content-secondary block mb-1">场景文案</label>
            <textarea
              defaultValue={selectedScene.text_content || ''}
              rows={3}
              className="w-full bg-background-elevated border border-border-subtle rounded-md px-2 py-1.5 text-sm outline-none focus:border-brand-500 resize-none"
            />
          </div>
          <div>
            <label className="text-xs text-content-secondary block mb-1">时长（秒）</label>
            <input
              type="number"
              defaultValue={selectedScene.duration}
              className="w-full bg-background-elevated border border-border-subtle rounded-md px-2 py-1.5 text-sm outline-none focus:border-brand-500"
            />
          </div>
        </div>
      ) : (
        <div className="space-y-5">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <Monitor className="w-4 h-4 text-brand-400" />
            项目属性
          </div>
          <div>
            <label className="text-xs text-content-secondary block mb-1">标题</label>
            <input
              type="text"
              defaultValue={project.title}
              className="w-full bg-background-elevated border border-border-subtle rounded-md px-2 py-1.5 text-sm outline-none focus:border-brand-500"
            />
          </div>
          <div>
            <label className="text-xs text-content-secondary block mb-1">画幅</label>
            <div className="flex gap-2">
              {['16:9', '9:16', '1:1'].map((ratio) => (
                <button
                  key={ratio}
                  className={clsx(
                    'flex-1 py-1.5 rounded-md text-xs border transition-colors',
                    project.target_format === ratio
                      ? 'bg-brand-900/50 text-brand-400 border-brand-900/60'
                      : 'bg-background-elevated text-content-secondary border-border-subtle hover:border-border-default'
                  )}
                >
                  {ratio}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="text-xs text-content-secondary block mb-1">目标时长</label>
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-content-tertiary" />
              <input
                type="number"
                defaultValue={project.target_duration || 30}
                className="flex-1 bg-background-elevated border border-border-subtle rounded-md px-2 py-1.5 text-sm outline-none focus:border-brand-500"
              />
              <span className="text-xs text-content-secondary">秒</span>
            </div>
          </div>
          <div className="border-t border-border-subtle pt-4">
            <div className="flex items-center gap-2 text-sm font-semibold mb-3">
              <Image className="w-4 h-4 text-brand-400" />
              素材
            </div>
            <div className="space-y-2">
              <div className="flex items-center gap-2 p-2 bg-background-elevated rounded-md border border-border-subtle">
                <div className="w-8 h-8 rounded bg-blue-600/30 flex items-center justify-center text-xs">图</div>
                <div className="text-xs truncate">product-shot.png</div>
              </div>
              <div className="flex items-center gap-2 p-2 bg-background-elevated rounded-md border border-border-subtle">
                <div className="w-8 h-8 rounded bg-emerald-600/30 flex items-center justify-center text-xs"><Music className="w-3.5 h-3.5" /></div>
                <div className="text-xs truncate">bgm-upbeat.mp3</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
