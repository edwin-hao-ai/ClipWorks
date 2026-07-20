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
          <label className="text-sm text-content-secondary">标题</label>
          <input
            type="text"
            value={script.title}
            onChange={(e) => update('title', e.target.value)}
            className="w-full rounded-md bg-background-elevated border border-border px-3 py-2 text-sm text-content-primary focus:outline-none focus:border-brand-500"
          />
        </div>
        <div className="space-y-1">
          <label className="text-sm text-content-secondary">钩子（前 3 秒）</label>
          <input
            type="text"
            value={script.hook}
            onChange={(e) => update('hook', e.target.value)}
            className="w-full rounded-md bg-background-elevated border border-border px-3 py-2 text-sm text-content-primary focus:outline-none focus:border-brand-500"
          />
        </div>
      </div>
      <div className="space-y-1">
        <label className="text-sm text-content-secondary">叙事弧线</label>
        <textarea
          value={script.narrative_arc}
          onChange={(e) => update('narrative_arc', e.target.value)}
          rows={3}
          className="w-full rounded-md bg-background-elevated border border-border px-3 py-2 text-sm text-content-primary focus:outline-none focus:border-brand-500"
        />
      </div>
      <div className="space-y-1">
        <label className="text-sm text-content-secondary">CTA</label>
        <input
          type="text"
          value={script.cta}
          onChange={(e) => update('cta', e.target.value)}
          className="w-full rounded-md bg-background-elevated border border-border px-3 py-2 text-sm text-content-primary focus:outline-none focus:border-brand-500"
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-1">
          <label className="text-sm text-content-secondary">时长（秒）</label>
          <input
            type="number"
            value={script.duration}
            onChange={(e) => update('duration', Number(e.target.value))}
            className="w-full rounded-md bg-background-elevated border border-border px-3 py-2 text-sm text-content-primary focus:outline-none focus:border-brand-500"
          />
        </div>
        <div className="space-y-1">
          <label className="text-sm text-content-secondary">画幅</label>
          <select
            value={script.format}
            onChange={(e) => update('format', e.target.value as AgentScript['format'])}
            className="w-full rounded-md bg-background-elevated border border-border px-3 py-2 text-sm text-content-primary focus:outline-none focus:border-brand-500"
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
