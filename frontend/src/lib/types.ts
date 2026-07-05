export interface User {
  id: string;
  email: string;
  name?: string;
  avatar_url?: string;
  provider?: string;
}

export interface Project {
  id: string;
  title: string;
  source_url?: string;
  source_type: 'url' | 'upload';
  status: 'draft' | 'generating' | 'ready' | 'failed';
  target_format: string;
  target_duration?: number;
  latest_output_url?: string;
  composition?: Composition;
  created_at: string;
  updated_at: string;
}

export interface Composition {
  id: string;
  width: number;
  height: number;
  duration: number;
  fps: number;
  metadata: Record<string, any>;
  tracks: Track[];
}

export interface Track {
  id: string;
  type: 'video' | 'image' | 'audio' | 'text' | 'overlay';
  index: number;
  name?: string;
  clips: Clip[];
}

export interface Clip {
  id: string;
  asset_id?: string;
  start_time: number;
  duration: number;
  position?: { x: number; y: number; width: number; height: number };
  style?: Record<string, any>;
  text_content?: string;
}

export interface RenderJob {
  id: string;
  status: string;
  progress: number;
  output_url?: string;
  html_output_url?: string;
  error_message?: string;
}

export interface MediaAsset {
  id: string;
  project_id: string;
  type: 'image' | 'video' | 'audio' | 'font' | 'generated';
  source: 'upload' | 'pexels' | 'generated' | 'user_url';
  original_url?: string;
  local_path?: string;
  thumbnail_url?: string;
  metadata?: Record<string, any>;
  created_at: string;
}

export interface Scene {
  id: string;
  index: number;
  name: string;
  description?: string;
  start_time: number;
  duration: number;
  thumbnail?: string;
  text_content?: string;
  visual_content?: string;
}

export interface PipelineStep {
  id: string;
  label: string;
  description?: string;
}
