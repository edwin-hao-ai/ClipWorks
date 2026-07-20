'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { AuthGuard } from '@/components/layout/AuthGuard';
import { AssetUploader } from '@/components/assets/AssetUploader';
import { AssetGrid } from '@/components/assets/AssetGrid';
import { MediaAsset } from '@/lib/types';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { ArrowLeft, ImagePlus } from 'lucide-react';

export default function AssetsPage() {
  const { id } = useParams<{ id: string }>();
  const [assets, setAssets] = useState<MediaAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.get(`/projects/${id}/assets/`);
      setAssets(Array.isArray(data) ? data : []);
    } catch (err) {
      setAssets([]);
      setError(err instanceof Error ? err.message : '加载素材失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [id]);

  if (loading) {
    return (
      <AuthGuard>
        <div className="min-h-dvh flex items-center justify-center bg-background-base text-content-secondary">
          <div className="flex flex-col items-center gap-4">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500" />
            <p className="text-sm">加载素材中…</p>
          </div>
        </div>
      </AuthGuard>
    );
  }

  if (error && assets.length === 0) {
    return (
      <AuthGuard>
        <div className="min-h-dvh flex items-center justify-center bg-background-base">
          <div className="text-center max-w-md">
            <p className="text-error mb-4">{error}</p>
            <Button onClick={() => load()}>重试</Button>
          </div>
        </div>
      </AuthGuard>
    );
  }

  return (
    <AuthGuard>
      <div className="flex min-h-dvh bg-background-base">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <TopBar title="素材库" />
          <main id="cw-main" className="flex-1 p-6 overflow-auto">
            <div className="flex items-center justify-between mb-2">
              <div>
                <h2 className="text-2xl font-bold text-content-primary">项目素材</h2>
                <p className="text-sm text-content-secondary mt-1">管理视频、图片、音频等创作素材</p>
              </div>
              <AssetUploader projectId={id} onUploaded={load} />
            </div>

            {/* Upload zone */}
            <AssetUploader projectId={id} onUploaded={load}>
              <div
                className={
                  'mt-5 mb-6 border-2 border-dashed rounded-md p-8 text-center bg-background-surface hover:border-brand-500/50 hover:bg-background-elevated transition-colors cursor-pointer ' +
                  'border-border-default'
                }
              >
                <ImagePlus className="w-8 h-8 mx-auto mb-2 text-content-tertiary" />
                <p className="text-sm text-content-secondary">拖拽文件到此处上传，或点击上方按钮</p>
              </div>
            </AssetUploader>

            {error && (
              <div className="mb-4 text-sm text-warning bg-warning/10 border border-warning/20 rounded-md px-4 py-3">
                {error}
              </div>
            )}

            {assets.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-20 bg-background-surface border border-border-subtle rounded-md text-content-secondary">
                <ImagePlus className="w-14 h-14 mb-4 text-content-tertiary" />
                <p className="text-lg font-medium text-content-primary mb-2">还没有素材</p>
                <p className="text-sm text-content-secondary mb-4">点击上传按钮添加你的第一个素材</p>
              </div>
            ) : (
              <AssetGrid assets={assets} projectId={id} onChanged={load} />
            )}

            <div className="mt-6">
              <Link
                href={`/projects/${id}`}
                className="text-sm text-content-secondary hover:text-content-primary flex items-center gap-1 transition-colors"
              >
                <ArrowLeft className="w-4 h-4" /> 返回工作区
              </Link>
            </div>
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}
