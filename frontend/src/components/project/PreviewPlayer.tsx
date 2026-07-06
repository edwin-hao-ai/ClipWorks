'use client';

import { VideoPreview } from './VideoPreview';

interface PreviewPlayerProps {
  videoUrl?: string;
  outputUrl?: string | null;
  htmlOutputUrl?: string | null;
  format?: '16:9' | '9:16' | '1:1';
}

export function PreviewPlayer({ videoUrl, outputUrl, htmlOutputUrl }: PreviewPlayerProps) {
  const effectiveOutputUrl = outputUrl ?? videoUrl ?? null;
  const effectiveHtmlOutputUrl = htmlOutputUrl ?? null;

  return (
    <VideoPreview outputUrl={effectiveOutputUrl} htmlOutputUrl={effectiveHtmlOutputUrl} />
  );
}
