'use client';

import { Project, Scene } from '@/lib/types';

interface PropertyPanelProps {
  project: Project;
  selectedScene?: Scene;
}

export function PropertyPanel({ project, selectedScene }: PropertyPanelProps) {
  return (
    <div className="bg-background-surface border border-border-subtle rounded-md p-5 h-full overflow-y-auto">
      <h3 className="font-semibold text-content-primary mb-4">属性</h3>
      <div className="space-y-4">
        <div>
          <label className="text-xs text-text-secondary">状态</label>
          <p className="text-sm text-content-primary">{project.status}</p>
        </div>
        {selectedScene ? (
          <div>
            <label className="text-xs text-text-secondary">当前场景</label>
            <p className="text-sm text-content-primary">{selectedScene.name}</p>
          </div>
        ) : (
          <p className="text-sm text-content-secondary">未选择场景</p>
        )}
      </div>
    </div>
  );
}
