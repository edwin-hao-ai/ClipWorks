'use client';

import { AgentScript, Project } from '@/lib/types';

export interface ScriptPanelProps {
  value?: AgentScript | null;
  project: Project;
  onChange: (script: AgentScript) => void;
}

export function ScriptPanel({ value, project, onChange }: ScriptPanelProps) {
  const script = value || {
    title: project.title,
    hook: '',
    roles: [],
    narrative_arc: '',
    cta: '',
    duration: project.target_duration || 30,
    format: (project.target_format as '16:9' | '9:16' | '1:1') || '16:9',
  };

  const update = <K extends keyof AgentScript>(key: K, val: AgentScript[K]) => {
    onChange({ ...script, [key]: val });
  };

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-1">
          <label htmlFor="script-title" className="text-sm text-content-secondary">标题</label>
          <input
            id="script-title"
            type="text"
            value={script.title}
            onChange={(e) => update('title', e.target.value)}
            className="w-full rounded-md bg-background-elevated border border-border px-3 py-2 text-sm text-content-primary focus-ring"
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="script-hook" className="text-sm text-content-secondary">钩子（前 3 秒）</label>
          <input
            id="script-hook"
            type="text"
            value={script.hook}
            onChange={(e) => update('hook', e.target.value)}
            className="w-full rounded-md bg-background-elevated border border-border px-3 py-2 text-sm text-content-primary focus-ring"
          />
        </div>
      </div>
      <div className="space-y-1">
        <label htmlFor="script-narrative" className="text-sm text-content-secondary">叙事弧线</label>
        <textarea
          id="script-narrative"
          value={script.narrative_arc}
          onChange={(e) => update('narrative_arc', e.target.value)}
          rows={3}
          className="w-full rounded-md bg-background-elevated border border-border px-3 py-2 text-sm text-content-primary focus-ring"
        />
      </div>
      <div className="space-y-1">
        <label htmlFor="script-cta" className="text-sm text-content-secondary">CTA</label>
        <input
          id="script-cta"
          type="text"
          value={script.cta}
          onChange={(e) => update('cta', e.target.value)}
          className="w-full rounded-md bg-background-elevated border border-border px-3 py-2 text-sm text-content-primary focus-ring"
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-1">
          <label htmlFor="script-duration" className="text-sm text-content-secondary">时长（秒）</label>
          <input
            id="script-duration"
            type="number"
            value={script.duration}
            onChange={(e) => update('duration', Number(e.target.value))}
            className="w-full rounded-md bg-background-elevated border border-border px-3 py-2 text-sm text-content-primary focus-ring"
          />
        </div>
        <div className="space-y-1">
          <label htmlFor="script-format" className="text-sm text-content-secondary">画幅</label>
          <select
            id="script-format"
            value={script.format}
            onChange={(e) => update('format', e.target.value as AgentScript['format'])}
            className="w-full rounded-md bg-background-elevated border border-border px-3 py-2 text-sm text-content-primary focus-ring"
          >
            <option value="16:9">16:9</option>
            <option value="9:16">9:16</option>
            <option value="1:1">1:1</option>
          </select>
        </div>
      </div>
    </div>
  );
}
