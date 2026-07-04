'use client';

import { useRef } from 'react';
import { Button } from '@/components/ui/Button';
import { Upload } from 'lucide-react';

interface Props {
  projectId: string;
  onUploaded: () => void;
}

export function AssetUploader({ projectId, onUploaded }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = async (file: File) => {
    const form = new FormData();
    form.append('file', file);
    await fetch(`${process.env.NEXT_PUBLIC_API_URL}/projects/${projectId}/assets/`, {
      method: 'POST',
      body: form,
    });
    onUploaded();
  };

  return (
    <div>
      <input
        ref={inputRef}
        type="file"
        className="hidden"
        onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
      />
      <Button onClick={() => inputRef.current?.click()}>
        <Upload className="w-4 h-4 mr-1" /> 上传素材
      </Button>
    </div>
  );
}
