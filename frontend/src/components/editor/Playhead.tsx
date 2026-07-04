interface Props {
  currentTime: number;
  duration: number;
  onSeek: (time: number) => void;
}

const PIXELS_PER_SECOND = 20;

export function Playhead({ currentTime, duration, onSeek }: Props) {
  const totalWidth = Math.max(duration * PIXELS_PER_SECOND, 400);

  return (
    <div
      className="relative h-8 border-b border-slate-200 bg-slate-50"
      style={{ width: totalWidth }}
      onClick={(e) => {
        const rect = e.currentTarget.getBoundingClientRect();
        const x = e.clientX - rect.left;
        onSeek(Math.max(0, x / PIXELS_PER_SECOND));
      }}
    >
      {Array.from({ length: Math.ceil(duration) + 1 }).map((_, i) => (
        <div
          key={i}
          className="absolute top-0 bottom-0 border-l border-slate-300 text-[10px] text-slate-500 pl-1"
          style={{ left: i * PIXELS_PER_SECOND }}
        >
          {i}s
        </div>
      ))}
      <div
        className="absolute top-0 bottom-0 w-0.5 bg-red-500 z-10"
        style={{ left: currentTime * PIXELS_PER_SECOND }}
      >
        <div className="absolute -top-1 -left-1.5 w-4 h-4 bg-red-500 rounded-full" />
      </div>
    </div>
  );
}
