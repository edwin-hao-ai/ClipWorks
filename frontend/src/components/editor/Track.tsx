import { Clip, Track as TrackType } from '@/lib/types';
import { ClipBlock } from './ClipBlock';
import { Film, Image, Music, Type, Sparkles } from 'lucide-react';

interface Props {
  track: TrackType;
  selectedClipId?: string;
  onSelectClip: (clipId: string) => void;
  onUpdateClip: (clip: Clip) => void;
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

export function Track({ track, selectedClipId, onSelectClip, onUpdateClip }: Props) {
  const Icon = trackIcons[track.type] || Film;
  const colorClass = trackColors[track.type] || 'text-content-secondary bg-background-hover';

  return (
    <div className="flex border-b border-border-subtle">
      <div className={`w-36 px-3 py-3 border-r border-border-subtle text-xs font-medium flex items-center gap-2 ${colorClass}`}>
        <Icon className="w-4 h-4" />
        {track.name || track.type}
      </div>
      <div className="flex-1 relative h-12 bg-background-base">
        {track.clips.map((clip) => (
          <ClipBlock
            key={clip.id}
            clip={clip}
            selected={clip.id === selectedClipId}
            onSelect={(c) => onSelectClip(c.id)}
            onUpdate={onUpdateClip}
          />
        ))}
      </div>
    </div>
  );
}
