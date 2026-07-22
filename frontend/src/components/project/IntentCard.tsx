'use client';

interface IntentCardProps {
  intent: { duration?: number; format?: string; style?: string; goal?: string };
  onConfirm: () => void;
  onEdit: (text: string) => void;
}

export function IntentCard({ intent, onConfirm, onEdit }: IntentCardProps) {
  return (
    <div className="bg-brand-900/20 border border-brand-500/30 rounded-xl p-4">
      <div className="text-brand-400 font-semibold text-sm mb-2">AI 理解的需求</div>
      <div className="space-y-1 text-sm text-content-secondary">
        {intent.goal && <p>目标：{intent.goal}</p>}
        {intent.duration && <p>时长：{intent.duration} 秒</p>}
        {intent.format && <p>画幅：{intent.format}</p>}
        {intent.style && <p>风格：{intent.style}</p>}
      </div>
      <div className="flex gap-2 mt-3">
        <button onClick={onConfirm} className="px-3 py-1.5 rounded bg-brand-600 text-white text-sm">确认</button>
        <button onClick={() => onEdit('')} className="px-3 py-1.5 rounded bg-background-elevated text-content-secondary text-sm">修改</button>
      </div>
    </div>
  );
}
