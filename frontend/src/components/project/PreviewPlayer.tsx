interface Props {
  videoUrl?: string;
}

export function PreviewPlayer({ videoUrl }: Props) {
  if (!videoUrl) {
    return (
      <div className="bg-black rounded-xl flex items-center justify-center text-white h-full min-h-[360px]">
        <p className="opacity-70">视频生成后即可在此预览</p>
      </div>
    );
  }

  return (
    <div className="bg-black rounded-xl overflow-hidden h-full flex items-center justify-center">
      <video
        src={videoUrl}
        controls
        className="max-w-full max-h-full"
        poster="/api/static/placeholder.png"
      />
    </div>
  );
}
