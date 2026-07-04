import { Play, Film } from 'lucide-react';

interface Props {
  videoUrl?: string;
}

export function PreviewPlayer({ videoUrl }: Props) {
  if (!videoUrl) {
    return (
      <div className="bg-black rounded-md flex flex-col items-center justify-center text-white h-full min-h-[360px]">
        <div className="relative mb-4">
          <div className="absolute inset-0 bg-brand-500/20 blur-xl rounded-full" />
          <div className="relative w-16 h-16 rounded-full bg-background-elevated/80 border border-border-default flex items-center justify-center">
            <Film className="w-7 h-7 text-content-tertiary" />
          </div>
        </div>
        <p className="text-content-secondary font-medium">视频将在这里预览</p>
        <p className="text-content-tertiary text-sm mt-1">点击「开始生成」后，成片会出现在此处</p>
      </div>
    );
  }

  return (
    <div className="bg-black rounded-md overflow-hidden h-full flex items-center justify-center relative group">
      <video
        src={videoUrl}
        controls
        className="max-w-full max-h-full"
        poster="/api/static/placeholder.png"
      />
    </div>
  );
}
