import { User, Project, MediaAsset, Composition } from './types';

export const DEMO_USER: User = {
  id: 'demo-user',
  name: 'Demo Creator',
  email: 'demo@clipworks.io',
  avatar_url: 'https://api.dicebear.com/7.x/avataaars/svg?seed=ClipWorks',
  provider: 'google',
};

export const DEMO_PROJECTS: Project[] = [
  {
    id: 'demo-saas-launch',
    title: 'SaaS 产品发布视频',
    source_url: 'https://clipworks.io',
    source_type: 'url',
    status: 'ready',
    target_format: '16:9',
    target_duration: 45,
    created_at: '2024-06-01T08:00:00Z',
    updated_at: '2024-06-01T10:30:00Z',
  },
  {
    id: 'demo-xhs-talk',
    title: '小红书口播精剪',
    source_url: 'upload',
    source_type: 'upload',
    status: 'ready',
    target_format: '9:16',
    target_duration: 32,
    created_at: '2024-06-02T09:15:00Z',
    updated_at: '2024-06-02T11:00:00Z',
  },
  {
    id: 'demo-release-notes',
    title: '功能更新说明',
    source_url: 'https://docs.clipworks.io',
    source_type: 'url',
    status: 'draft',
    target_format: '16:9',
    target_duration: 60,
    created_at: '2024-06-03T07:30:00Z',
    updated_at: '2024-06-03T07:30:00Z',
  },
];

export const DEMO_SCRIPT = [
  { tag: '钩子', content: '还在手动做产品视频？试试 ClipWorks，一键生成。' },
  { tag: '场景 1', content: '展示产品首页截图，突出核心卖点。' },
  { tag: '场景 2', content: '用户痛点 + 解决方案动画。' },
  { tag: '场景 3', content: '真实用户证言/数据展示。' },
  { tag: '结尾', content: '行动号召，访问官网。' },
];

export const DEMO_ASSETS: MediaAsset[] = [
  {
    id: 'asset-logo',
    project_id: 'demo-saas-launch',
    type: 'image',
    source: 'upload',
    original_url: 'logo.svg',
    thumbnail_url: '/api/static/logo.svg',
    created_at: '2024-06-01T08:05:00Z',
  },
  {
    id: 'asset-screenshot-1',
    project_id: 'demo-saas-launch',
    type: 'image',
    source: 'upload',
    original_url: 'product-screenshot-1.png',
    thumbnail_url: '/api/static/screenshot-1.png',
    created_at: '2024-06-01T08:10:00Z',
  },
  {
    id: 'asset-screenshot-2',
    project_id: 'demo-saas-launch',
    type: 'image',
    source: 'upload',
    original_url: 'product-screenshot-2.png',
    thumbnail_url: '/api/static/screenshot-2.png',
    created_at: '2024-06-01T08:15:00Z',
  },
  {
    id: 'asset-bg-music',
    project_id: 'demo-saas-launch',
    type: 'audio',
    source: 'upload',
    original_url: 'background-music.mp3',
    created_at: '2024-06-01T08:20:00Z',
  },
  {
    id: 'asset-voiceover',
    project_id: 'demo-saas-launch',
    type: 'audio',
    source: 'generated',
    original_url: 'voiceover-sample.mp3',
    created_at: '2024-06-01T08:25:00Z',
  },
];

export function getDemoProjectById(id: string): Project | undefined {
  return DEMO_PROJECTS.find((p) => p.id === id);
}

export function getDemoComposition(projectId: string): Composition {
  return {
    id: `comp-${projectId}`,
    width: 1920,
    height: 1080,
    duration: 45,
    fps: 30,
    metadata: {},
    tracks: [
      {
        id: 'track-video',
        type: 'video',
        index: 0,
        name: '视频',
        clips: [
          { id: 'clip-1', asset_id: 'asset-screenshot-1', start_time: 0, duration: 12, text_content: '产品首页' },
          { id: 'clip-2', asset_id: 'asset-screenshot-2', start_time: 14, duration: 14, text_content: '功能展示' },
          { id: 'clip-3', asset_id: 'asset-logo', start_time: 30, duration: 10, text_content: '品牌 Logo' },
        ],
      },
      {
        id: 'track-text',
        type: 'text',
        index: 1,
        name: '字幕',
        clips: [
          { id: 'clip-t1', start_time: 0, duration: 8, text_content: '钩子文案' },
          { id: 'clip-t2', start_time: 14, duration: 10, text_content: '卖点说明' },
          { id: 'clip-t3', start_time: 36, duration: 8, text_content: '行动号召' },
        ],
      },
      {
        id: 'track-audio',
        type: 'audio',
        index: 2,
        name: '音频',
        clips: [
          { id: 'clip-a1', asset_id: 'asset-bg-music', start_time: 0, duration: 45, text_content: '背景音乐' },
          { id: 'clip-a2', asset_id: 'asset-voiceover', start_time: 2, duration: 20, text_content: '旁白' },
        ],
      },
    ],
  };
}

export function formatDuration(seconds?: number): string {
  if (seconds === undefined) return '--:--';
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}
