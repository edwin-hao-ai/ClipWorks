'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { AuthGuard } from '@/components/layout/AuthGuard';
import { AssetUploader } from '@/components/assets/AssetUploader';
import { AssetGrid } from '@/components/assets/AssetGrid';
import { MediaAsset } from '@/lib/types';
import { api } from '@/lib/api';

export default function AssetsPage() {
  const { id } = useParams<{ id: string }>();
  const [assets, setAssets] = useState<MediaAsset[]>([]);

  const load = async () => {
    const data = await api.get(`/projects/${id}/assets/`);
    setAssets(data);
  };

  useEffect(() => {
    load();
  }, [id]);

  return (
    <AuthGuard>
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="flex-1 flex flex-col">
          <TopBar title="素材库" />
          <main className="flex-1 p-8">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-semibold text-slate-900">项目素材</h2>
              <AssetUploader projectId={id} onUploaded={load} />
            </div>
            {assets.length === 0 ? (
              <div className="text-center py-20 text-slate-500 bg-white rounded-xl border border-slate-200">
                还没有素材，点击上传
              </div>
            ) : (
              <AssetGrid assets={assets} />
            )}
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}
