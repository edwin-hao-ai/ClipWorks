'use client';

import { useRef, useState } from 'react';
import { Button } from '@/components/ui/Button';
import { api } from '@/lib/api';
import { Upload } from 'lucide-react';

interface Props {
  projectId: string;
  onUploaded: () => void;
  children?: React.ReactNode;
}

export function AssetUploader({ projectId, onUploaded, children }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);

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

  const onDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const onDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  };

  return (
    <div
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      className={`rounded-lg border-2 border-dashed p-4 transition-colors ${
        dragOver ? 'border-primary bg-primary/10' : 'border-transparent'
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        className="hidden"
        onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
      />
      {children ? (
        <div onClick={() => inputRef.current?.click()}>{children}</div>
      ) : (
        <Button onClick={() => inputRef.current?.click()} disabled={uploading}>
          <Upload className="w-4 h-4 mr-1.5" /> 上传素材
        </Button>
      )}
      {error && (
        <p className="mt-2 text-sm text-error">{error}</p>
      )}
    </div>
  );
}
