'use client';

interface VideoPreviewProps {
  outputUrl: string | null;
  htmlOutputUrl: string | null;
}

export function VideoPreview({ outputUrl, htmlOutputUrl }: VideoPreviewProps) {
  if (outputUrl) {
    return (
      <div className="w-full h-full flex flex-col">
        <div className="text-sm text-content-secondary mb-2 px-1">成片预览</div>
        <video
          src={outputUrl}
          controls
          className="w-full rounded-lg bg-black"
          style={{ maxHeight: 'calc(100% - 28px)' }}
        />
        <a
          href={outputUrl}
          download
          className="mt-3 inline-flex items-center justify-center px-4 py-2 bg-brand-600 hover:bg-brand-500 text-white rounded-lg text-sm font-medium transition-colors"
        >
          下载 MP4
        </a>
      </div>
    );
  }

  if (htmlOutputUrl) {
    return (
      <div className="w-full h-full flex flex-col">
        <div className="text-sm text-content-secondary mb-2 px-1">HTML 预览</div>
        <iframe
          src={htmlOutputUrl}
          className="w-full flex-1 rounded-lg bg-black border-0"
          title="HTML preview"
        />
      </div>
    );
  }

  return (
    <div className="w-full h-full flex items-center justify-center text-content-tertiary text-sm">
      暂无预览
    </div>
  );
}
