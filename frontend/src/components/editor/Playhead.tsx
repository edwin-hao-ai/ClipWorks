interface Props {
  currentTime: number;
  duration: number;
  pixelsPerSecond: number;
  onSeek: (time: number) => void;
}

export function Playhead({ currentTime, duration, pixelsPerSecond, onSeek }: Props) {
  const totalWidth = Math.max(duration * pixelsPerSecond, 400);

  return (
    <div
      className="relative h-8 border-b border-border-subtle bg-background-surface"
      style={{ width: totalWidth }}
      onClick={(e) => {
        const rect = e.currentTarget.getBoundingClientRect();
        const scrollLeft = e.currentTarget.parentElement?.scrollLeft || 0;
        const x = e.clientX - rect.left + scrollLeft;
        onSeek(Math.max(0, x / pixelsPerSecond));
      }}
    >
      {Array.from({ length: Math.ceil(duration) + 1 }).map((_, i) => (
        <div
          key={i}
          className="absolute top-0 bottom-0 border-l border-border-default text-[10px] text-content-tertiary pl-1 select-none"
          style={{ left: i * pixelsPerSecond }}
        >
          {i}s
        </div>
      ))}
      <div
        className="absolute top-0 bottom-0 w-0.5 bg-error z-10"
        style={{ left: currentTime * pixelsPerSecond }}
      >
        <div className="absolute -top-1 -left-1.5 w-0 h-0 border-l-[6px] border-l-transparent border-r-[6px] border-r-transparent border-t-[8px] border-t-error" />
      </div>
    </div>
  );
}
