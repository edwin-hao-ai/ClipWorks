import { ScrollText } from 'lucide-react';
import { DEMO_SCRIPT } from '@/lib/demoData';

interface Props {
  sourceUrl?: string;
}

export function ScriptPanel({ sourceUrl }: Props) {
  return (
    <div className="bg-background-surface border border-border-subtle rounded-md p-5">
      <h3 className="font-semibold text-content-primary mb-4 flex items-center gap-2">
        <ScrollText className="w-4 h-4 text-brand-400" /> 脚本大纲
      </h3>
      <div className="space-y-3 text-sm text-content-secondary">
        {DEMO_SCRIPT.map((item, index) => (
          <div
            key={index}
            className="p-3 bg-background-elevated border border-border-subtle rounded-md hover:border-border-default transition-colors"
          >
            <span className="font-medium text-content-primary">{item.tag}：</span>
            {item.tag === '结尾' ? (
              <>
                {item.content.replace('官网', '')}
                <span className="text-brand-400">{sourceUrl || '官网'}</span>。
              </>
            ) : (
              item.content
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
