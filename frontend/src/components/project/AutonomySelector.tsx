'use client';

interface Props {
  value: 'confirm_each' | 'confirm_render_only' | 'full_auto';
  onChange: (value: Props['value']) => void;
}

const OPTIONS = [
  { value: 'confirm_each', label: '每步都确认' },
  { value: 'confirm_render_only', label: '仅渲染前确认' },
  { value: 'full_auto', label: '全自动' },
] as const;

export function AutonomySelector({ value, onChange }: Props) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value as Props['value'])}
      className="bg-background-elevated border border-border-subtle text-content-primary text-xs rounded-md px-2 py-1 focus:outline-none focus:border-brand-500"
      aria-label="Agent 自主级别"
    >
      {OPTIONS.map((opt) => (
        <option key={opt.value} value={opt.value}>
          {opt.label}
        </option>
      ))}
    </select>
  );
}
