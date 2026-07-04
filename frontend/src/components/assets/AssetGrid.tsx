import { MediaAsset } from '@/lib/types';
import { Image, Film, Music, File, FileText } from 'lucide-react';

interface Props {
  assets: MediaAsset[];
}

const iconMap: Record<string, typeof File> = {
  image: Image,
  video: Film,
  audio: Music,
  font: FileText,
  generated: File,
};

const typeLabels: Record<string, string> = {
  image: '图片',
  video: '视频',
  audio: '音频',
  font: '字体',
  generated: '生成',
};

const typeColors: Record<string, string> = {
  image: 'text-timeline-image bg-timeline-image/10 border-timeline-image/20',
  video: 'text-timeline-video bg-timeline-video/10 border-timeline-video/20',
  audio: 'text-timeline-audio bg-timeline-audio/10 border-timeline-audio/20',
  font: 'text-content-secondary bg-background-hover',
  generated: 'text-timeline-overlay bg-timeline-overlay/10 border-timeline-overlay/20',
};

export function AssetGrid({ assets }: Props) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
      {assets.map((asset) => {
        const Icon = iconMap[asset.type] || File;
        return (
          <div
            key={asset.id}
            className="group bg-background-surface border border-border-subtle rounded-md p-4 text-center hover:border-border-default hover:-translate-y-0.5 hover:shadow-md transition-all duration-200 ease-cinematic"
          >
            <div className="aspect-square rounded-md bg-background-elevated flex items-center justify-center mb-3 group-hover:bg-background-hover transition-colors">
              <Icon className="w-10 h-10 text-content-tertiary group-hover:text-content-secondary transition-colors" />
            </div>
            <p className="text-xs text-content-primary truncate mb-1.5">{asset.original_url || asset.local_path}</p>
            <span className={`inline-block text-[10px] px-2 py-0.5 rounded-full border ${typeColors[asset.type] || 'text-content-secondary bg-background-hover'}`}>
              {typeLabels[asset.type] || asset.type}
            </span>
          </div>
        );
      })}
    </div>
  );
}
