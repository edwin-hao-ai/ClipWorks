'use client';

import { useState } from 'react';
import { Clip, MediaAsset, Track } from '@/lib/types';
import { api, API_URL } from '@/lib/api';
import { Image, Film, Music, File, FileText, Trash2, Link2, ListPlus, Check } from 'lucide-react';

interface Props {
  assets: MediaAsset[];
  projectId?: string;
  onChanged?: () => void;
}

const iconMap: Record<string, typeof File> = {
  image: Image,
  video: Film,
  audio: Music,
  font: FileText,
  generated: File,
};

const typeLabels: Record<string, string> = {
  image: '图片',
  video: '视频',
  audio: '音频',
  font: '字体',
  generated: '生成',
};

const typeColors: Record<string, string> = {
  image: 'text-timeline-image bg-timeline-image/10 border-timeline-image/20',
  video: 'text-timeline-video bg-timeline-video/10 border-timeline-video/20',
  audio: 'text-timeline-audio bg-timeline-audio/10 border-timeline-audio/20',
  font: 'text-content-secondary bg-background-hover',
  generated: 'text-timeline-overlay bg-timeline-overlay/10 border-timeline-overlay/20',
};

// 素材类型 -> 时间线轨道类型。字体/生成类暂不支持直接入轨。
function trackTypeFor(asset: MediaAsset): Track['type'] | null {
  if (asset.type === 'image' || asset.type === 'video' || asset.type === 'audio') return asset.type;
  return null;
}

const trackName: Record<string, string> = { image: '画面', video: '视频', audio: '音频' };

function defaultDuration(asset: MediaAsset): number {
  const meta = asset.metadata_?.duration;
  if (typeof meta === 'number' && meta > 0) return Math.round(meta * 10) / 10;
  return asset.type === 'image' ? 3 : 5;
}

function genId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
}

// 读取 API 根地址；测试环境对 @/lib/api 做部分 mock 时可能没有 API_URL 导出，需兜底。
function getApiBase(): string {
  try {
    return API_URL || 'http://localhost:8000';
  } catch {
    return 'http://localhost:8000';
  }
}

// 选择一个可在浏览器里直接预览的素材地址。
// 优先把本地 data/assets/（含 backend/data/assets/ 遗留路径）映射到同源 /api/static/，
// 因为外部 http(s) 图床可能跨域/失效；没有本地路径时才使用外链或兜底。
function getAssetUrl(asset: MediaAsset): string | null {
  const candidates = [
    asset.local_path,
    asset.original_url,
    asset.thumbnail_url,
  ].filter(Boolean) as string[];
  if (candidates.length === 0) return null;

  // 本地路径：统一提取 project_id 之后的相对路径，映射到 /api/static。
  for (const raw of candidates) {
    for (const marker of ['/data/assets/', '\\data\\assets\\']) {
      const idx = raw.indexOf(marker);
      if (idx >= 0) {
        const rel = raw.slice(idx + marker.length).replace(/\\/g, '/');
        return `/api/static/${rel}`;
      }
    }
  }

  const raw = candidates.find((r) => !r.includes('data/assets')) || candidates[0];
  if (/^https?:\/\//i.test(raw)) return raw;
  if (raw.startsWith('/api/static/')) return raw;

  // 兜底：相对路径补 API_BASE。
  const base = getApiBase();
  return `${base}${raw.startsWith('/') ? '' : '/'}${raw}`;
}

// 返回一个备用预览 URL：主 URL 失败时尝试外链（如果是本地 static URL）。
function getFallbackUrl(asset: MediaAsset): string | null {
  if (!asset.local_path || !asset.original_url) return null;
  if (/^https?:\/\//i.test(asset.original_url)) return asset.original_url;
  return null;
}

export function AssetGrid({ assets, projectId, onChanged }: Props) {
  const [error, setError] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [addingId, setAddingId] = useState<string | null>(null);
  const [addedId, setAddedId] = useState<string | null>(null);
  // 缩略图加载失败时回退到类型图标；删除改为两步内联确认（替代 window.confirm）。
  const [brokenThumbs, setBrokenThumbs] = useState<Set<string>>(new Set());
  const [fallbackUrls, setFallbackUrls] = useState<Record<string, string>>({});
  const [confirmingId, setConfirmingId] = useState<string | null>(null);

  const showError = (msg: string) => {
    setError(msg);
    window.setTimeout(() => setError(null), 3000);
  };

  const handleDelete = async (asset: MediaAsset) => {
    if (!projectId) return;
    // 第一次点击只进入确认态（3 秒后自动复位），第二次点击才真正删除。
    if (confirmingId !== asset.id) {
      setConfirmingId(asset.id);
      window.setTimeout(() => setConfirmingId((cur) => (cur === asset.id ? null : cur)), 3000);
      return;
    }
    setConfirmingId(null);
    setDeletingId(asset.id);
    try {
      await api.delete(`/projects/${projectId}/assets/${asset.id}`);
      onChanged?.();
    } catch (err) {
      showError(err instanceof Error ? err.message : '删除失败');
    } finally {
      setDeletingId(null);
    }
  };

  const handleCopy = async (asset: MediaAsset) => {
    const url = getAssetUrl(asset);
    if (!url || !navigator.clipboard) return;
    try {
      await navigator.clipboard.writeText(url);
      setCopiedId(asset.id);
      window.setTimeout(() => setCopiedId((cur) => (cur === asset.id ? null : cur)), 1500);
    } catch (err) {
      showError(err instanceof Error ? err.message : '复制失败');
    }
  };

  // 把素材作为片段写入合成：取整段合成 -> 找到/新建匹配轨道 -> 末尾追加引用该素材的片段 -> 整体 PUT。
  const handleAddToTimeline = async (asset: MediaAsset) => {
    if (!projectId) return;
    const tType = trackTypeFor(asset);
    if (!tType) return;
    setAddingId(asset.id);
    try {
      const comp = await api.get(`/compositions/${projectId}`);
      const tracks: Track[] = Array.isArray(comp.tracks) ? [...comp.tracks] : [];
      let target = tracks.find((t) => t.type === tType);
      if (!target) {
        const nextIndex = tracks.reduce((m, t) => Math.max(m, t.index ?? 0), -1) + 1;
        target = { id: genId('track'), type: tType, index: nextIndex, name: trackName[tType], clips: [] };
        tracks.push(target);
      }
      const lastEnd = target.clips.reduce(
        (m, c) => Math.max(m, (c.start_time || 0) + (c.duration || 0)),
        0,
      );
      const clip: Clip = {
        id: genId('clip'),
        asset_id: asset.id,
        start_time: lastEnd,
        duration: defaultDuration(asset),
      };
      target.clips = [...target.clips, clip];
      await api.put(`/compositions/${projectId}`, { ...comp, tracks });
      setAddedId(asset.id);
      window.setTimeout(() => setAddedId((cur) => (cur === asset.id ? null : cur)), 1500);
    } catch (err) {
      showError(err instanceof Error ? err.message : '加入时间线失败');
    } finally {
      setAddingId(null);
    }
  };

  return (
    <>
      {error && (
        <div className="mb-3 text-sm text-error bg-error/10 border border-error/20 rounded-md px-4 py-2">
          {error}
        </div>
      )}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-5 gap-4">
        {assets.map((asset) => {
          const Icon = iconMap[asset.type] || File;
          const url = getAssetUrl(asset);
          const hasUrl = !!url;
          const canAdd = !!projectId && !!trackTypeFor(asset);
          const metaName = typeof asset.metadata_?.name === 'string' ? asset.metadata_.name : undefined;
          // 展示名优先级：后端写入的主题名 > URL 末段（去掉查询串）> 本地文件名 > id。
          // 自动配图的 picsum URL 末段是「1080」这类无意义字符，必须靠主题名兜底。
          const name =
            metaName ||
            asset.original_url?.split('/').pop()?.split('?')[0] ||
            asset.local_path?.split('/').pop() ||
            asset.id;
          const showThumb = hasUrl && !brokenThumbs.has(asset.id) && (asset.type === 'image' || asset.type === 'video');
          const confirming = confirmingId === asset.id;
          return (
            <div
              key={asset.id}
              className="group relative bg-background-surface border border-border-subtle rounded-md p-4 text-center hover:border-border-default hover:-translate-y-0.5 hover:shadow-md transition-all duration-200 ease-cinematic"
            >
              {projectId && (
                <button
                  type="button"
                  aria-label={confirming ? '确认删除' : '删除'}
                  title={confirming ? '再次点击确认删除' : '删除'}
                  disabled={deletingId === asset.id}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDelete(asset);
                  }}
                  className={`focus-ring absolute top-1.5 right-1.5 p-1.5 rounded-md transition-all disabled:opacity-50 ${
                    confirming
                      ? 'bg-error text-content-inverse opacity-100'
                      : 'bg-background-elevated/90 text-content-tertiary hover:text-error hover:bg-error/10 opacity-0 group-hover:opacity-100 focus:opacity-100'
                  }`}
                >
                  {confirming ? <Check className="w-3.5 h-3.5" /> : <Trash2 className="w-3.5 h-3.5" />}
                </button>
              )}
              <div className="relative aspect-square rounded-md bg-background-elevated flex items-center justify-center mb-3 group-hover:bg-background-hover transition-colors overflow-hidden">
                {showThumb && asset.type === 'image' && (
                  <img
                    src={fallbackUrls[asset.id] || url}
                    alt={name}
                    loading="lazy"
                    onError={() => {
                      const fallback = getFallbackUrl(asset);
                      if (fallback && fallbackUrls[asset.id] !== fallback) {
                        setFallbackUrls((prev) => ({ ...prev, [asset.id]: fallback }));
                      } else {
                        setBrokenThumbs((s) => new Set(s).add(asset.id));
                      }
                    }}
                    className="absolute inset-0 w-full h-full object-cover"
                  />
                )}
                {showThumb && asset.type === 'video' && (
                  <video
                    src={fallbackUrls[asset.id] || url}
                    muted
                    playsInline
                    preload="metadata"
                    onError={() => {
                      const fallback = getFallbackUrl(asset);
                      if (fallback && fallbackUrls[asset.id] !== fallback) {
                        setFallbackUrls((prev) => ({ ...prev, [asset.id]: fallback }));
                      } else {
                        setBrokenThumbs((s) => new Set(s).add(asset.id));
                      }
                    }}
                    className="absolute inset-0 w-full h-full object-cover"
                  />
                )}
                {!showThumb && (
                  <Icon className="w-10 h-10 text-content-tertiary group-hover:text-content-secondary transition-colors" />
                )}
              </div>
              <p className="text-xs text-content-primary truncate mb-1.5">{name}</p>
              <span className={`inline-block text-[10px] px-2 py-0.5 rounded-full border ${typeColors[asset.type] || 'text-content-secondary bg-background-hover'}`}>
                {typeLabels[asset.type] || asset.type}
              </span>
              {canAdd && (
                <button
                  type="button"
                  disabled={addingId === asset.id}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleAddToTimeline(asset);
                  }}
                  className="focus-ring mt-2 inline-flex items-center gap-1 text-[11px] text-content-secondary hover:text-brand-400 transition-colors disabled:opacity-50"
                >
                  <ListPlus className="w-3 h-3" />
                  {addedId === asset.id ? '已加入' : addingId === asset.id ? '加入中…' : '加入时间线'}
                </button>
              )}
              {hasUrl && (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleCopy(asset);
                  }}
                  className="focus-ring mt-1.5 inline-flex items-center gap-1 text-[11px] text-content-secondary hover:text-brand-400 transition-colors"
                >
                  <Link2 className="w-3 h-3" />
                  {copiedId === asset.id ? '已复制' : '复制链接'}
                </button>
              )}
            </div>
          );
        })}
      </div>
    </>
  );
}
