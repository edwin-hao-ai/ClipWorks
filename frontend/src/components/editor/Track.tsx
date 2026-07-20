import { Clip, Track as TrackType } from '@/lib/types';
import { ClipBlock } from './ClipBlock';
import { Film, Image, Music, Type, Sparkles, Plus } from 'lucide-react';

interface Props {
  track: TrackType;
  pixelsPerSecond: number;
  selectedClipId?: string;
  onSelectClip: (clipId: string) => void;
  onAddClip: (trackId: string) => void;
  onChangeClip?: (clipId: string, patch: Partial<Clip>) => void;
}

const trackIcons: Record<string, typeof Film> = {
  video: Film,
  image: Image,
  audio: Music,
  text: Type,
  overlay: Sparkles,
};

const trackColors: Record<string, string> = {
  video: 'text-timeline-video bg-timeline-video/10',
  image: 'text-timeline-image bg-timeline-image/10',
  audio: 'text-timeline-audio bg-timeline-audio/10',
  text: 'text-timeline-text bg-timeline-text/10',
  overlay: 'text-timeline-overlay bg-timeline-overlay/10',
};

export function Track({ track, pixelsPerSecond, selectedClipId, onSelectClip, onAddClip, onChangeClip }: Props) {
  const Icon = trackIcons[track.type] || Film;
  const colorClass = trackColors[track.type] || 'text-content-secondary bg-background-hover';

  return (
    <div className="flex border-b border-border-subtle">
      <div className={`w-36 px-3 py-2 border-r border-border-subtle text-xs font-medium flex flex-col justify-center gap-1.5 ${colorClass}`}>
        <div className="flex items-center gap-2">
          <Icon className="w-4 h-4" />
          <span className="truncate">{track.name || track.type}</span>
        </div>
        <button
          type="button"
          onClick={() => onAddClip(track.id)}
          className="self-start flex items-center gap-1 px-1.5 py-0.5 rounded text-[11px] text-content-primary bg-background-base/50 hover:bg-background-base/80 transition-colors"
        >
          <Plus className="w-3 h-3" /> 添加片段
        </button>
      </div>
      <div className="flex-1 relative h-12 bg-background-base">
        {track.clips.map((clip) => (
          <ClipBlock
            key={clip.id}
            clip={clip}
            pixelsPerSecond={pixelsPerSecond}
            selected={clip.id === selectedClipId}
            trackType={track.type}
            onSelect={(c) => onSelectClip(c.id)}
            onChange={onChangeClip ? (patch) => onChangeClip(clip.id, patch) : undefined}
          />
        ))}
      </div>
    </div>
  );
}
