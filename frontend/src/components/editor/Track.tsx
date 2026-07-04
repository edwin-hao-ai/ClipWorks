import { Track as TrackType } from '@/lib/types';
import { ClipBlock } from './ClipBlock';

interface Props {
  track: TrackType;
  selectedClipId?: string;
  onSelectClip: (clipId: string) => void;
  onUpdateClip: (clip: any) => void;
}

export function Track({ track, selectedClipId, onSelectClip, onUpdateClip }: Props) {
  return (
    <div className="flex border-b border-slate-200">
      <div className="w-32 px-3 py-3 bg-slate-50 border-r border-slate-200 text-xs font-medium text-slate-700">
        {track.name || track.type}
      </div>
      <div className="flex-1 relative h-14 bg-white">
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
