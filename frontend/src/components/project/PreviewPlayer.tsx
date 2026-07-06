'use client';

import { clsx } from 'clsx';
import { VideoPreview } from './VideoPreview';

interface PreviewPlayerProps {
  videoUrl?: string;
  outputUrl?: string | null;
  htmlOutputUrl?: string | null;
  format?: '16:9' | '9:16' | '1:1';
}

const FORMAT_RATIO: Record<string, string> = {
  '16:9': 'aspect-video',
  '9:16': 'aspect-[9/16]',
  '1:1': 'aspect-square',
};

export function PreviewPlayer({
  videoUrl,
  outputUrl,
  htmlOutputUrl,
  format = '16:9',
}: PreviewPlayerProps) {
  const effectiveOutputUrl = outputUrl ?? videoUrl ?? null;
  const effectiveHtmlOutputUrl = htmlOutputUrl ?? null;

  return (
    <div className="w-full h-full flex flex-col items-center justify-center bg-black">
      <div
        className={clsx(
          'w-full max-h-full',
          FORMAT_RATIO[format] || 'aspect-video'
        )}
      >
        <VideoPreview outputUrl={effectiveOutputUrl} htmlOutputUrl={effectiveHtmlOutputUrl} />
      </div>
    </div>
  );
}
