import { Button } from '@/components/ui/Button';
import { Download } from 'lucide-react';

interface Props {
  mp4Url?: string;
  htmlUrl?: string;
}

export function DownloadButtons({ mp4Url, htmlUrl }: Props) {
  if (!mp4Url && !htmlUrl) return null;

  return (
    <div className="flex gap-3">
      {mp4Url && (
        <a href={mp4Url} download>
          <Button variant="secondary" size="sm">
            <Download className="w-4 h-4 mr-1" /> 下载 MP4
          </Button>
        </a>
      )}
      {htmlUrl && (
        <a href={htmlUrl} download>
          <Button variant="secondary" size="sm">
            <Download className="w-4 h-4 mr-1" /> 下载 HTML
          </Button>
        </a>
      )}
    </div>
  );
}
