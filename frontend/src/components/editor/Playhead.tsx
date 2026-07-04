import { PIXELS_PER_SECOND } from './ClipBlock';

interface Props {
  currentTime: number;
  duration: number;
  onSeek: (time: number) => void;
}

export function Playhead({ currentTime, duration, onSeek }: Props) {
  const totalWidth = Math.max(duration * PIXELS_PER_SECOND, 400);

  return (
    <div
      className="relative h-8 border-b border-border-subtle bg-background-surface"
      style={{ width: totalWidth }}
      onClick={(e) => {
        const rect = e.currentTarget.getBoundingClientRect();
        const scrollLeft = e.currentTarget.parentElement?.scrollLeft || 0;
        const x = e.clientX - rect.left + scrollLeft;
        onSeek(Math.max(0, x / PIXELS_PER_SECOND));
      }}
    >
      {Array.from({ length: Math.ceil(duration) + 1 }).map((_, i) => (
        <div
          key={i}
          className="absolute top-0 bottom-0 border-l border-border-default text-[10px] text-content-tertiary pl-1 select-none"
          style={{ left: i * PIXELS_PER_SECOND }}
        >
          {i}s
        </div>
      ))}
      <div
        className="absolute top-0 bottom-0 w-0.5 bg-error z-10"
        style={{ left: currentTime * PIXELS_PER_SECOND }}
      >
        <div className="absolute -top-1 -left-1.5 w-0 h-0 border-l-[6px] border-l-transparent border-r-[6px] border-r-transparent border-t-[8px] border-t-error" />
      </div>
    </div>
  );
}
