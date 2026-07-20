'use client';

import { useEffect, useState } from 'react';
import { Project, Scene, MediaAsset } from '@/lib/types';
import { clsx } from 'clsx';
import { Type, Clock, Monitor, Image as ImageIcon, Music, Video, File, Check, Upload, Link2 } from 'lucide-react';

interface PropertyPanelProps {
  project: Project;
  selectedScene?: Scene;
  assets?: MediaAsset[];
  onChange?: (changes: Partial<Project> | Partial<Scene>) => void;
  onSceneApply?: (scene: Partial<Scene>) => void;
  onProjectSave?: (changes: Partial<Project>) => void;
  onUpload?: () => void;
  applying?: boolean;
  saving?: boolean;
}

const ASSET_ICON: Record<MediaAsset['type'], typeof ImageIcon> = {
  image: ImageIcon,
  video: Video,
  audio: Music,
  font: File,
  generated: ImageIcon,
};

export function PropertyPanel({
  project,
  selectedScene,
  assets = [],
  onChange,
  onSceneApply,
  onProjectSave,
  onUpload,
  applying,
  saving,
}: PropertyPanelProps) {
  const [projectForm, setProjectForm] = useState({
    title: project.title,
    source_url: project.source_url ?? '',
    target_format: project.target_format,
    target_duration: project.target_duration ?? 30,
  });

  const [sceneForm, setSceneForm] = useState({
    name: selectedScene?.name ?? '',
    text_content: selectedScene?.text_content ?? '',
    duration: selectedScene?.duration ?? 0,
  });

  useEffect(() => {
    setProjectForm({
      title: project.title,
      source_url: project.source_url ?? '',
      target_format: project.target_format,
      target_duration: project.target_duration ?? 30,
    });
  }, [project]);

  useEffect(() => {
    setSceneForm({
      name: selectedScene?.name ?? '',
      text_content: selectedScene?.text_content ?? '',
      duration: selectedScene?.duration ?? 0,
    });
  }, [selectedScene]);

  const handleProjectChange = (field: keyof typeof projectForm, value: string | number) => {
    setProjectForm((prev) => ({ ...prev, [field]: value }));
    // 只上报变化的字段：整表上传会让父组件误以为画幅每次都变，逐键触发真实渲染。
    onChange?.({ [field]: value } as Partial<Project>);
  };

  const handleSceneChange = (field: keyof typeof sceneForm, value: string | number) => {
    setSceneForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSaveProject = () => {
    const changes: Partial<Project> = {};
    if (projectForm.title !== project.title) changes.title = projectForm.title;
    if (projectForm.source_url !== (project.source_url ?? '')) changes.source_url = projectForm.source_url;
    if (projectForm.target_duration !== (project.target_duration ?? 30)) changes.target_duration = projectForm.target_duration;
    if (Object.keys(changes).length > 0) {
      onProjectSave?.(changes);
    }
  };

  const hasProjectChanges =
    projectForm.title !== project.title ||
    projectForm.source_url !== (project.source_url ?? '') ||
    projectForm.target_duration !== (project.target_duration ?? 30);

  if (selectedScene) {
    return (
      <div className="bg-background-surface border border-border-subtle rounded-lg p-4 h-full overflow-y-auto">
        <div className="space-y-5">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <Type className="w-4 h-4 text-brand-400" />
            场景属性
          </div>
          <div>
            <label className="text-xs text-content-secondary block mb-1">场景名称</label>
            <input
              type="text"
              value={sceneForm.name}
              onChange={(e) => handleSceneChange('name', e.target.value)}
              className="w-full bg-background-elevated border border-border-subtle rounded-md px-2 py-1.5 text-sm outline-none focus:border-brand-500"
            />
          </div>
          <div>
            <label className="text-xs text-content-secondary block mb-1">场景文案</label>
            <textarea
              value={sceneForm.text_content}
              onChange={(e) => handleSceneChange('text_content', e.target.value)}
              rows={3}
              className="w-full bg-background-elevated border border-border-subtle rounded-md px-2 py-1.5 text-sm outline-none focus:border-brand-500 resize-none"
            />
          </div>
          <div>
            <label className="text-xs text-content-secondary block mb-1">时长（秒）</label>
            <input
              type="number"
              value={sceneForm.duration}
              onChange={(e) => handleSceneChange('duration', Number(e.target.value))}
              className="w-full bg-background-elevated border border-border-subtle rounded-md px-2 py-1.5 text-sm outline-none focus:border-brand-500"
            />
          </div>
          <button
            type="button"
            disabled={applying}
            onClick={() => onSceneApply?.(sceneForm)}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-md bg-brand-600 text-content-inverse text-sm font-medium hover:bg-brand-500 disabled:opacity-50 transition-colors"
          >
            {applying ? (
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <Check className="w-4 h-4" />
            )}
            {applying ? '应用中…' : '应用修改'}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-background-surface border border-border-subtle rounded-lg p-4 h-full overflow-y-auto">
      <div className="space-y-5">
        <div className="flex items-center gap-2 text-sm font-semibold">
          <Monitor className="w-4 h-4 text-brand-400" />
          项目属性
        </div>
        <div>
          <label className="text-xs text-content-secondary block mb-1">标题</label>
          <input
            type="text"
            value={projectForm.title}
            onChange={(e) => handleProjectChange('title', e.target.value)}
            className="w-full bg-background-elevated border border-border-subtle rounded-md px-2 py-1.5 text-sm outline-none focus:border-brand-500"
          />
        </div>
        <div>
          <label className="text-xs text-content-secondary block mb-1 flex items-center gap-1">
            <Link2 className="w-3 h-3" /> 素材来源 URL
          </label>
          <input
            type="text"
            value={projectForm.source_url}
            onChange={(e) => handleProjectChange('source_url', e.target.value)}
            placeholder="粘贴网页链接，AI 会自动抓取图片/文案"
            className="w-full bg-background-elevated border border-border-subtle rounded-md px-2 py-1.5 text-sm outline-none focus:border-brand-500 placeholder-content-tertiary"
          />
        </div>
        <div>
          <label className="text-xs text-content-secondary block mb-1">画幅</label>
          <div className="flex gap-2">
            {['16:9', '9:16', '1:1'].map((ratio) => (
              <button
                key={ratio}
                type="button"
                onClick={() => handleProjectChange('target_format', ratio)}
                className={clsx(
                  'flex-1 py-1.5 rounded-md text-xs border transition-colors',
                  projectForm.target_format === ratio
                    ? 'bg-brand-600 text-content-inverse border-brand-600'
                    : 'bg-background-elevated text-content-secondary border-border-subtle hover:border-border-default'
                )}
              >
                {ratio}
              </button>
            ))}
          </div>
        </div>
        <div>
          <label className="text-xs text-content-secondary block mb-1">目标时长</label>
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-content-tertiary" />
            <input
              type="number"
              value={projectForm.target_duration}
              onChange={(e) => handleProjectChange('target_duration', Number(e.target.value))}
              className="flex-1 bg-background-elevated border border-border-subtle rounded-md px-2 py-1.5 text-sm outline-none focus:border-brand-500"
            />
            <span className="text-xs text-content-secondary">秒</span>
          </div>
        </div>

        {hasProjectChanges && (
          <button
            type="button"
            disabled={saving}
            onClick={handleSaveProject}
            className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-md bg-brand-600 text-content-inverse text-sm font-medium hover:bg-brand-500 disabled:opacity-50 transition-colors"
          >
            {saving ? (
              <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
            ) : (
              <Check className="w-4 h-4" />
            )}
            {saving ? '保存中…' : '保存项目属性'}
          </button>
        )}

        <div className="border-t border-border-subtle pt-4">
          <div className="flex items-center justify-between text-sm font-semibold mb-3">
            <div className="flex items-center gap-2">
              <ImageIcon className="w-4 h-4 text-brand-400" />
              素材
            </div>
            <button
              type="button"
              onClick={onUpload}
              className="text-xs flex items-center gap-1 text-brand-400 hover:text-brand-300 transition-colors"
            >
              <Upload className="w-3 h-3" /> 上传
            </button>
          </div>
          {assets.length === 0 ? (
            <div className="text-xs text-content-tertiary bg-background-elevated rounded-md p-3 border border-border-subtle">
              暂无素材。上传图片/视频/音频，或设置上方 URL 让 AI 抓取。
            </div>
          ) : (
            <div className="space-y-2">
              {assets.map((asset) => {
                const Icon = ASSET_ICON[asset.type] || File;
                const name = asset.original_url?.split('/').pop() || asset.local_path?.split('/').pop() || asset.id;
                return (
                  <div
                    key={asset.id}
                    className="flex items-center gap-2 p-2 bg-background-elevated rounded-md border border-border-subtle"
                  >
                    <div className="w-8 h-8 rounded bg-brand-900/40 flex items-center justify-center text-xs text-brand-400">
                      <Icon className="w-4 h-4" />
                    </div>
                    <div className="text-xs truncate flex-1" title={name}>
                      {name}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
