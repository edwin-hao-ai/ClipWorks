import { Project } from '@/lib/types';
import Link from 'next/link';
import { Trash2, Play, Clock } from 'lucide-react';
import { formatDuration } from '@/lib/demoData';

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

const statusClasses: Record<string, string> = {
  draft: 'bg-background-hover text-content-secondary',
  generating: 'bg-warning/15 text-warning',
  ready: 'bg-success/15 text-success',
  failed: 'bg-error/15 text-error',
};

const gradientMap: Record<string, string> = {
  'demo-saas-launch': 'from-brand-600 to-violet-600',
  'demo-xhs-talk': 'from-pink-500 to-orange-500',
  'demo-release-notes': 'from-emerald-500 to-teal-600',
};

export function ProjectCard({ project, onDelete }: ProjectCardProps) {
  const gradient = gradientMap[project.id] || 'from-slate-700 to-slate-600';

  return (
    <div className="group bg-background-surface border border-border-subtle rounded-md overflow-hidden hover:border-border-default hover:-translate-y-0.5 hover:shadow-md transition-all duration-200 ease-cinematic">
      <Link href={`/projects/${project.id}`} className={`block relative aspect-video bg-gradient-to-br ${gradient}`}>
        <div className={`absolute inset-0 bg-gradient-to-br ${gradient} opacity-80`} />
        <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity duration-200 bg-black/30">
          <div className="w-12 h-12 rounded-full bg-white/20 backdrop-blur flex items-center justify-center">
            <Play className="w-5 h-5 text-white fill-white" />
          </div>
        </div>
        <div className="absolute bottom-2 right-2 px-1.5 py-0.5 rounded bg-black/50 text-white text-xs font-mono">
          {formatDuration(project.target_duration)}
        </div>
      </Link>
      <div className="p-4">
        <div className="flex justify-between items-start mb-2">
          <Link href={`/projects/${project.id}`} className="font-semibold text-content-primary hover:text-brand-400 transition-colors line-clamp-1">
            {project.title}
          </Link>
          <button
            onClick={() => onDelete(project.id)}
            aria-label="Delete"
            className="text-content-tertiary hover:text-error transition-colors shrink-0 ml-2"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
        <p className="text-sm text-content-tertiary mb-4 truncate">{project.source_url || '无来源链接'}</p>
        <div className="flex items-center justify-between text-xs">
          <span className={`px-2 py-1 rounded-full font-medium ${statusClasses[project.status]}`}>
            {statusMap[project.status]}
          </span>
          <span className="text-content-tertiary flex items-center gap-1">
            <Clock className="w-3 h-3" /> {project.target_format}
          </span>
        </div>
      </div>
    </div>
  );
}
