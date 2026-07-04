import { MediaAsset } from '@/lib/types';
import { Image, Film, Music, File } from 'lucide-react';

interface Props {
  assets: MediaAsset[];
}

const iconMap: Record<string, any> = {
  image: Image,
  video: Film,
  audio: Music,
};

export function AssetGrid({ assets }: Props) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
      {assets.map((asset) => {
        const Icon = iconMap[asset.type] || File;
        return (
          <div key={asset.id} className="bg-white rounded-xl border border-slate-200 p-4 text-center">
            <Icon className="w-10 h-10 mx-auto mb-2 text-slate-400" />
            <p className="text-xs text-slate-700 truncate">{asset.original_url}</p>
            <span className="text-[10px] text-slate-400 uppercase">{asset.type}</span>
          </div>
        );
      })}
    </div>
  );
}
