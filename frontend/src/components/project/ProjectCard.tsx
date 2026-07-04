import { Project } from '@/lib/types';
import Link from 'next/link';
import { Trash2 } from 'lucide-react';

interface ProjectCardProps {
  project: Project;
  onDelete: (id: string) => void;
}

const statusMap: Record<string, string> = {
  draft: '草稿',
  generating: '生成中',
  ready: '已完成',
  failed: '失败',
};

export function ProjectCard({ project, onDelete }: ProjectCardProps) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 hover:shadow-sm transition-shadow">
      <div className="flex justify-between items-start mb-3">
        <Link href={`/projects/${project.id}`} className="font-semibold text-slate-900 hover:text-brand-600">
          {project.title}
        </Link>
        <button
          onClick={() => onDelete(project.id)}
          className="text-slate-400 hover:text-red-500"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
      <p className="text-sm text-slate-500 mb-4 truncate">{project.source_url || '无来源链接'}</p>
      <div className="flex items-center justify-between text-xs">
        <span
          className={`px-2 py-1 rounded-full ${
            project.status === 'ready'
              ? 'bg-green-50 text-green-700'
              : project.status === 'generating'
              ? 'bg-amber-50 text-amber-700'
              : 'bg-slate-100 text-slate-600'
          }`}
        >
          {statusMap[project.status]}
        </span>
        <span className="text-slate-400">{project.target_format}</span>
      </div>
    </div>
  );
}
