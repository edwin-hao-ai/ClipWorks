interface Props {
  videoUrl?: string;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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
        poster={`${API_URL}/api/static/placeholder.png`}
      />
    </div>
  );
}
