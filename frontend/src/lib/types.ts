export interface User {
  id: string;
  email: string;
  name?: string;
  avatar_url?: string;
  provider?: string;
}

export type AgentStep =
  | 'idle'
  | 'understand'
  | 'script'
  | 'assets'
  | 'scenes'
  | 'effects'
  | 'render'
  | 'approved'
  | 'chatting'
  | 'pending_approval'
  | 'generating';

export interface AgentScript {
  title: string;
  hook: string;
  roles: { name: string; perspective: string }[];
  narrative_arc: string;
  cta: string;
  duration: number;
  format: '16:9' | '9:16' | '1:1';
  style?: string;
  mood?: string;
  rhythm?: string;
}

export interface AgentAssetItem {
  type: 'image' | 'video' | 'music' | 'generated_image';
  description: string;
  query: string;
  count: number;
}

export interface AgentAssetPlan {
  needed: AgentAssetItem[];
}

export interface AgentSceneItem {
  start: number;
  duration: number;
  description: string;
  visual: string;
  text: string;
  visual_type: 'product' | 'broll' | 'metaphor' | 'text';
  shot: string;
  transition: string;
  lower_third: string;
  required_assets: number[];
  narration?: string;
  visual_style?: string;
  animation_keywords?: string[];
  generate_image?: boolean;
  generate_image_prompt?: string;
}

export interface AgentScenePlan {
  scenes: AgentSceneItem[];
}

export interface AgentEffectItem {
  scene_index: number;
  visual_style: string;
  animation_keywords: string[];
  generate_image: boolean;
  generate_image_prompt: string;
}

export interface AgentEffectPlan {
  effects: AgentEffectItem[];
}

export interface AgentUnderstandPayload {
  summary?: string;
  duration?: number;
  format?: string;
  audience?: string;
  style?: string;
  platform?: string;
  cta?: string;
}

export interface AgentScriptPayload {
  title?: string;
  hook?: string;
  narrative_arc?: string;
  cta?: string;
  duration?: number;
  format?: string;
}

export interface AgentAssetsPayload {
  needed?: { description?: string; source?: string }[];
}

export interface AgentScenesPayload {
  scenes?: Scene[];
}

export interface AgentEffectsPayload {
  effects?: { scene_index?: number; visual_style?: string; animation_keywords?: string[] }[];
}

export interface AgentState {
  step: AgentStep;
  generating_step?: AgentStep | null;
  messages?: { role: 'user' | 'assistant'; content: string }[];
  pending_plan?: AgentPlan | null;
  script?: AgentScript | null;
  assets?: AgentAssetPlan | null;
  scenes?: AgentScenePlan | null;
  effects?: AgentEffectPlan | null;
  autonomy_level?: 'confirm_each' | 'confirm_render_only' | 'full_auto';
  payload?: {
    understand?: AgentUnderstandPayload;
    script?: AgentScriptPayload;
    assets?: AgentAssetsPayload;
    scenes?: AgentScenesPayload;
    effects?: AgentEffectsPayload;
  };
  pending_user_confirmation?: boolean;
}

export interface AgentPlan {
  final_plan?: boolean;
  title: string;
  hook: string;
  format: '16:9' | '9:16' | '1:1';
  duration: number;
  scenes: AgentScene[];
  assets_needed: string[];
  engine_hint: 'hyperframes' | 'remotion' | 'video-use';
}

export interface AgentScene {
  start: number;
  duration: number;
  description: string;
  visual: string;
  text: string;
  narration?: string;
}

export interface Project {
  id: string;
  title: string;
  source_url?: string;
  source_type: 'url' | 'upload';
  status: 'draft' | 'planning' | 'generating' | 'ready' | 'failed';
  target_format: string;
  target_duration?: number;
  agent_state?: AgentState;
  latest_output_url?: string;
  cover_url?: string | null;
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
  metadata: Record<string, unknown>;
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
  style?: Record<string, unknown>;
  text_content?: string;
}

export interface RenderJob {
  id: string;
  status: string;
  progress: number;
  logs?: { time: string; message: string }[];
  output_url?: string;
  html_output_url?: string;
  error_message?: string;
  stalled_reason?: string;
  queue_position?: number;
  is_placeholder?: boolean;
  created_at?: string;
}

export interface MediaAsset {
  id: string;
  project_id: string;
  type: 'image' | 'video' | 'audio' | 'font' | 'generated';
  source: 'upload' | 'pexels' | 'stock' | 'generated' | 'user_url';
  original_url?: string;
  local_path?: string;
  thumbnail_url?: string;
  // 后端 ORM 属性名为 metadata_（DB 列名 metadata），原样序列化输出。
  metadata_?: Record<string, unknown>;
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

export type VibeEventType =
  | 'token'
  | 'artifact'
  | 'question'
  | 'progress'
  | 'error'
  | 'done';

export interface VibeArtifact {
  kind: 'understand' | 'script' | 'assets' | 'scenes' | 'effects' | 'render';
  data: unknown;
}

export type VibeEvent =
  | { type: 'token'; token: string }
  | { type: 'artifact'; artifact: VibeArtifact }
  | { type: 'question'; question: string; options?: string[] }
  | { type: 'progress'; step: string; progress: number; message?: string }
  | { type: 'error'; message: string; code?: string }
  | { type: 'done'; payload?: AgentState['payload'] };
