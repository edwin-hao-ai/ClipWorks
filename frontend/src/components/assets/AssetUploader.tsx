'use client';

import { useRef, useState } from 'react';
import { Button } from '@/components/ui/Button';
import { api } from '@/lib/api';
import { Upload } from 'lucide-react';

interface Props {
  projectId: string;
  onUploaded: () => void;
}

export function AssetUploader({ projectId, onUploaded }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  const handleFile = async (file: File) => {
    setError(null);
    setUploading(true);
    try {
      const form = new FormData();
      form.append('file', file);
      await api.postForm(`/projects/${projectId}/assets/`, form);
      onUploaded();
    } catch (err) {
      setError(err instanceof Error ? err.message : '上传失败');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div>
      <input
        ref={inputRef}
        type="file"
        className="hidden"
        onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
      />
      <Button onClick={() => inputRef.current?.click()} disabled={uploading}>
        <Upload className="w-4 h-4 mr-1" /> 上传素材
      </Button>
      {error && (
        <p className="mt-2 text-sm text-red-600">{error}</p>
      )}
    </div>
  );
}
