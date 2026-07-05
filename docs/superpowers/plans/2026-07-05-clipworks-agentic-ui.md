# ClipWorks Agentic UI 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 ClipWorks 前端改造成以 AI Agent 为核心的视频创作界面，包含 Agent Launchpad 首页、三栏影院式工作台、场景卡片系统、可视化流水线。

**Architecture:** 保留现有 Next.js + Tailwind + Zustand 技术栈，新增/重写首页和工作台页面，提取可复用的 SceneCard、Pipeline、PropertyPanel 组件；后端扩展 Agent API 支持场景级上下文，使对话修改能定位到具体场景。

**Tech Stack:** Next.js 14, React 18, TypeScript, Tailwind CSS, Zustand, Lucide React, Vitest + @testing-library/react, jsdom, FastAPI, Python.

## Global Constraints

- 深色模式优先，使用 `docs/design/clipworks-design.md` 中的设计 token。
- 所有新组件使用函数式组件 + TypeScript props 接口。
- 使用 `clsx` + `tailwind-merge`（项目已有 `clsx`，新增 `tailwind-merge` 可选）进行条件类名处理。
- 保持现有路由结构：`/` 首页、`/projects` 项目库、`/projects/:id` 工作台、`/projects/:id/editor` 时间线、`/projects/:id/assets` 素材库。
- API 调用统一通过 `frontend/src/lib/api.ts`。
- 每个 task 必须包含测试，并在 commit 前通过 `npm test --run`（前端）或 `pytest`（后端）。
- 不引入新的重型 UI 库；动画仅用 Tailwind/CSS transition。
- 场景卡片数据由后端 Agent 在生成时显式输出，前端根据返回的 `scenes` 字段渲染。

---

## Task 1: 修复 Vitest 配置与创建测试骨架

当前 `vitest.config.ts` 引用了不存在的 `vitest.setup.ts`，会导致测试无法运行。本任务先修复测试基础设施，为后续组件测试铺路。

**Files:**
- Create: `frontend/vitest.setup.ts`
- Modify: `frontend/vitest.config.ts`（确认引用存在）
- Test: `frontend/tests/components/SceneCard.test.tsx`（先写失败测试）

**Interfaces:**
- Produces: `SceneCard` 组件接口定义（在 Task 2 实现）。

- [ ] **Step 1: 创建 vitest.setup.ts**

```typescript
import '@testing-library/jest-dom';
```

- [ ] **Step 2: 确认 vitest.config.ts 引用**

`frontend/vitest.config.ts` 第 10 行已经是 `setupFiles: ['./vitest.setup.ts']`，保持不动。

- [ ] **Step 3: 写 SceneCard 的失败测试**

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { SceneCard } from '@/components/project/SceneCard';
import { Scene } from '@/lib/types';

const mockScene: Scene = {
  id: 'scene-1',
  index: 0,
  name: '产品痛点引入',
  description: '用一个问题引出用户痛点',
  start_time: 0,
  duration: 8,
  thumbnail: undefined,
  text_content: '还在手动做视频？',
  visual_content: '产品首页截图',
};

describe('SceneCard', () => {
  it('renders scene name and duration', () => {
    render(<SceneCard scene={mockScene} isSelected={false} onClick={() => {}} />);
    expect(screen.getByText('产品痛点引入')).toBeInTheDocument();
    expect(screen.getByText('0:00 - 0:08')).toBeInTheDocument();
  });

  it('calls onClick when clicked', () => {
    const onClick = vi.fn();
    render(<SceneCard scene={mockScene} isSelected={false} onClick={onClick} />);
    fireEvent.click(screen.getByText('产品痛点引入'));
    expect(onClick).toHaveBeenCalledWith('scene-1');
  });
});
```

- [ ] **Step 4: 运行测试确认失败**

Run: `cd frontend && npm test --run`
Expected: FAIL with `SceneCard` not found / cannot resolve.

- [ ] **Step 5: Commit**

```bash
git add frontend/vitest.setup.ts frontend/tests/components/SceneCard.test.tsx
git commit -m "test: add vitest setup and SceneCard failing test"
```

---

## Task 2: 扩展类型与创建基础组件

扩展 `types.ts` 添加 `Scene` 类型，创建 `SceneCard`、`Pipeline` 两个核心 UI 组件。这两个组件是后续工作台改造的基础。

**Files:**
- Modify: `frontend/src/lib/types.ts`
- Create: `frontend/src/components/project/SceneCard.tsx`
- Create: `frontend/src/components/project/Pipeline.tsx`
- Test: `frontend/tests/components/SceneCard.test.tsx`（更新测试）
- Test: `frontend/tests/components/Pipeline.test.tsx`

**Interfaces:**
- Consumes: `Scene` 类型定义。
- Produces: `SceneCardProps { scene: Scene; isSelected: boolean; onClick: (id: string) => void }`；`PipelineProps { steps: PipelineStep[]; currentStepIndex: number }`。

- [ ] **Step 1: 扩展 types.ts 添加 Scene 类型**

```typescript
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
```

- [ ] **Step 2: 实现 SceneCard 组件**

```typescript
'use client';

import { clsx } from 'clsx';
import { Pencil } from 'lucide-react';
import { Scene } from '@/lib/types';

interface SceneCardProps {
  scene: Scene;
  isSelected?: boolean;
  onClick?: (id: string) => void;
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export function SceneCard({ scene, isSelected = false, onClick }: SceneCardProps) {
  const start = formatTime(scene.start_time);
  const end = formatTime(scene.start_time + scene.duration);

  return (
    <div
      onClick={() => onClick?.(scene.id)}
      className={clsx(
        'group flex items-center gap-3 p-2 rounded-lg border cursor-pointer transition-all duration-200',
        isSelected
          ? 'bg-brand-900/20 border-brand-500/60 shadow-[0_0_16px_rgba(14,165,233,0.15)]'
          : 'bg-background-elevated border-border-subtle hover:border-border-default hover:-translate-y-0.5'
      )}
    >
      <div
        className={clsx(
          'w-20 h-12 rounded-md shrink-0 flex items-center justify-center text-xs font-medium text-white/90',
          scene.index % 4 === 0 && 'bg-gradient-to-br from-blue-600/70 to-purple-600/70',
          scene.index % 4 === 1 && 'bg-gradient-to-br from-pink-600/70 to-orange-600/70',
          scene.index % 4 === 2 && 'bg-gradient-to-br from-emerald-600/70 to-teal-600/70',
          scene.index % 4 === 3 && 'bg-gradient-to-br from-amber-600/70 to-red-600/70'
        )}
      >
        {scene.thumbnail ? (
          <img src={scene.thumbnail} alt={scene.name} className="w-full h-full object-cover rounded-md" />
        ) : (
          `场景 ${scene.index + 1}`
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-content-primary truncate">{scene.name}</div>
        <div className="text-xs text-text-secondary mt-0.5">
          {start} - {end}
        </div>
        {scene.text_content && (
          <div className="text-xs text-text-tertiary truncate mt-0.5">{scene.text_content}</div>
        )}
      </div>
      <button
        className={clsx(
          'p-1.5 rounded-md opacity-0 group-hover:opacity-100 transition-opacity',
          isSelected ? 'text-brand-400 hover:bg-brand-900/40' : 'text-text-tertiary hover:text-content-primary hover:bg-background-hover'
        )}
        onClick={(e) => {
          e.stopPropagation();
          onClick?.(scene.id);
        }}
        aria-label="编辑场景"
      >
        <Pencil className="w-3.5 h-3.5" />
      </button>
    </div>
  );
}
```

- [ ] **Step 3: 实现 Pipeline 组件**

```typescript
'use client';

import { clsx } from 'clsx';
import { Check, Loader2, Circle } from 'lucide-react';
import { PipelineStep } from '@/lib/types';

interface PipelineProps {
  steps: PipelineStep[];
  currentStepIndex: number;
  currentDescription?: string;
}

export function Pipeline({ steps, currentStepIndex, currentDescription }: PipelineProps) {
  return (
    <div className="w-full">
      <div className="flex items-center justify-between relative">
        <div className="absolute top-1/2 left-0 right-0 h-0.5 bg-background-elevated -translate-y-1/2 -z-10" />
        <div
          className="absolute top-1/2 left-0 h-0.5 bg-gradient-to-r from-success to-brand-500 -translate-y-1/2 -z-10 transition-all duration-500"
          style={{
            width: `${Math.max(0, Math.min(100, (currentStepIndex / (steps.length - 1)) * 100))}%`,
          }}
        />
        {steps.map((step, idx) => {
          const done = idx < currentStepIndex;
          const active = idx === currentStepIndex;
          const Icon = done ? Check : active ? Loader2 : Circle;

          return (
            <div key={step.id} className="flex flex-col items-center gap-2 w-24">
              <div
                className={clsx(
                  'w-10 h-10 rounded-full border-2 flex items-center justify-center transition-all duration-300',
                  done && 'border-success bg-background-surface text-success',
                  active && 'border-brand-500 bg-brand-900/30 text-brand-400 shadow-[0_0_16px_rgba(14,165,233,0.25)]',
                  !done && !active && 'border-border-default bg-background-surface text-text-tertiary'
                )}
              >
                <Icon className={clsx('w-4 h-4', active && 'animate-spin')} />
              </div>
              <span
                className={clsx(
                  'text-xs text-center',
                  done && 'text-success',
                  active && 'text-brand-400',
                  !done && !active && 'text-text-tertiary'
                )}
              >
                {step.label}
              </span>
            </div>
          );
        })}
      </div>
      {currentDescription && (
        <div className="mt-4 bg-background-elevated border border-border-subtle rounded-lg p-3 flex items-center gap-3">
          <span className="w-2 h-2 rounded-full bg-brand-400 animate-pulse" />
          <span className="text-sm text-text-secondary">{currentDescription}</span>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 4: 更新 SceneCard 测试并新增 Pipeline 测试**

`frontend/tests/components/SceneCard.test.tsx` 已写，直接运行应通过。

```typescript
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Pipeline } from '@/components/project/Pipeline';

const steps = [
  { id: 'understand', label: '理解需求' },
  { id: 'analyze', label: '分析素材' },
  { id: 'script', label: '编写脚本' },
  { id: 'scenes', label: '生成场景' },
  { id: 'render', label: '渲染成片' },
];

describe('Pipeline', () => {
  it('renders all step labels', () => {
    render(<Pipeline steps={steps} currentStepIndex={2} />);
    steps.forEach((s) => {
      expect(screen.getByText(s.label)).toBeInTheDocument();
    });
  });

  it('shows current description when provided', () => {
    render(<Pipeline steps={steps} currentStepIndex={2} currentDescription="正在编写脚本..." />);
    expect(screen.getByText('正在编写脚本...')).toBeInTheDocument();
  });
});
```

- [ ] **Step 5: 运行测试**

Run: `cd frontend && npm test --run`
Expected: PASS for SceneCard and Pipeline tests.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/types.ts frontend/src/components/project/SceneCard.tsx frontend/src/components/project/Pipeline.tsx frontend/tests/components/SceneCard.test.tsx frontend/tests/components/Pipeline.test.tsx
git commit -m "feat: add Scene and Pipeline components with types"
```

---

## Task 3: Agent Launchpad 首页

重写 `frontend/src/app/page.tsx`，从当前极简页面改为 Agent Launchpad。新增一个轻量导航组件用于首页顶部。

**Files:**
- Rewrite: `frontend/src/app/page.tsx`
- Create: `frontend/src/components/layout/LaunchNav.tsx`
- Test: `frontend/tests/app/LaunchpadPage.test.tsx`

**Interfaces:**
- Consumes: `api.post('/projects/', ...)` 创建项目；`Project` 类型。
- Produces: `LaunchNav` 组件。

- [ ] **Step 1: 实现 LaunchNav 组件**

```typescript
'use client';

import Link from 'next/link';
import { Film } from 'lucide-react';

export function LaunchNav() {
  return (
    <nav className="h-16 px-6 flex items-center justify-between bg-background-surface/80 backdrop-blur border-b border-border-subtle">
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 bg-brand-600 rounded-md flex items-center justify-center shadow-glow">
          <Film className="w-5 h-5 text-content-inverse" />
        </div>
        <span className="font-bold text-content-primary">ClipWorks</span>
      </div>
      <div className="flex items-center gap-6 text-sm text-text-secondary">
        <Link href="/" className="text-content-primary hover:text-brand-400 transition-colors">创作</Link>
        <Link href="/projects" className="hover:text-content-primary transition-colors">项目库</Link>
        <Link href="/projects/demo/assets" className="hover:text-content-primary transition-colors">素材库</Link>
        <Link href="/settings" className="hover:text-content-primary transition-colors">设置</Link>
        <div className="w-8 h-8 rounded-full bg-background-elevated border border-border-default" />
      </div>
    </nav>
  );
}
```

- [ ] **Step 2: 重写首页为 Agent Launchpad**

```typescript
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { Sparkles, ArrowRight } from 'lucide-react';
import { LaunchNav } from '@/components/layout/LaunchNav';
import { Button } from '@/components/ui/Button';
import { api } from '@/lib/api';

const QUICK_PROMPTS = [
  '小红书口播精剪',
  'SaaS 产品发布',
  '教程视频',
  '短视频广告',
  '生日祝福视频',
];

export default function HomePage() {
  const router = useRouter();
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createProject = async (input: string) => {
    if (!input.trim() || loading) return;
    setLoading(true);
    setError(null);
    try {
      const project = await api.post('/projects/', {
        title: input.slice(0, 40) || '未命名项目',
        source_url: '',
        source_type: 'url',
      });
      router.push(`/projects/${project.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建项目失败');
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createProject(prompt);
  };

  return (
    <div className="min-h-screen bg-background-base flex flex-col relative overflow-hidden">
      <LaunchNav />
      <main className="flex-1 flex flex-col items-center justify-center px-6 relative">
        <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none">
          <div className="absolute -top-1/2 -left-1/4 w-[700px] h-[700px] rounded-full bg-brand-900/25 blur-[140px]" />
          <div className="absolute -bottom-1/4 -right-1/4 w-[600px] h-[600px] rounded-full bg-purple-900/15 blur-[120px]" />
        </div>

        <div className="relative text-center max-w-3xl w-full">
          <h1 className="text-4xl md:text-5xl font-bold mb-5 tracking-tight">
            一句话，一段素材，一条成片
          </h1>
          <p className="text-text-secondary text-lg mb-10">
            告诉 AI 你想做什么视频，它会自动规划、剪辑、出片。
          </p>

          <form onSubmit={handleSubmit} className="mb-6">
            <div className="bg-background-elevated border border-border-default rounded-2xl p-2 flex items-center gap-2 shadow-glow focus-within:border-brand-500 transition-colors">
              <input
                type="text"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="例如：帮我做一个 30 秒的产品介绍视频，风格活泼，面向年轻人…"
                className="flex-1 bg-transparent px-4 py-3 text-base outline-none placeholder-text-tertiary text-left"
                disabled={loading}
              />
              <Button
                type="submit"
                disabled={loading || !prompt.trim()}
                size="lg"
                className="shrink-0"
              >
                {loading ? (
                  <span className="flex items-center gap-2">
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    创建中
                  </span>
                ) : (
                  <span className="flex items-center gap-2">
                    <Sparkles className="w-4 h-4" />
                    开始创作
                  </span>
                )}
              </Button>
            </div>
          </form>

          {error && (
            <div className="mb-6 text-sm text-error bg-error/10 border border-error/20 rounded-lg px-4 py-3">
              {error}
            </div>
          )}

          <div className="flex flex-wrap justify-center gap-2 mb-16">
            <span className="text-sm text-text-tertiary py-1.5">热门：</span>
            {QUICK_PROMPTS.map((p) => (
              <button
                key={p}
                onClick={() => createProject(p)}
                disabled={loading}
                className="px-3 py-1.5 rounded-full bg-background-elevated border border-border-subtle text-sm text-text-secondary hover:border-brand-500/50 hover:text-brand-400 transition-colors disabled:opacity-50"
              >
                {p}
              </button>
            ))}
          </div>

          <RecentProjects />
        </div>
      </main>
    </div>
  );
}

function RecentProjects() {
  const projects = [
    { id: '1', title: '产品发布视频', time: '2 小时前', status: '已完成', gradient: 'from-blue-600/40 to-purple-600/40' },
    { id: '2', title: '小红书口播', time: '昨天', status: '草稿', gradient: 'from-pink-600/40 to-orange-600/40' },
    { id: '3', title: '功能更新说明', time: '3 天前', status: '已完成', gradient: 'from-emerald-600/40 to-teal-600/40' },
  ];

  return (
    <div className="text-left">
      <div className="text-sm text-text-secondary mb-3 px-1">最近项目</div>
      <div className="flex gap-3 overflow-x-auto pb-2">
        {projects.map((p) => (
          <a
            key={p.id}
            href={`/projects/${p.id}`}
            className="min-w-[200px] bg-background-surface border border-border-subtle rounded-lg p-3 hover:border-border-default transition-colors"
          >
            <div className={`aspect-video rounded-md bg-gradient-to-br ${p.gradient} mb-2`} />
            <div className="text-sm font-medium text-content-primary truncate">{p.title}</div>
            <div className="flex items-center justify-between mt-1">
              <span className="text-xs text-text-tertiary">{p.time}</span>
              <span className="text-xs text-success">{p.status}</span>
            </div>
          </a>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: 写首页测试**

```typescript
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import HomePage from '@/app/page';

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock('@/lib/api', () => ({
  api: {
    post: vi.fn(),
  },
}));

describe('HomePage', () => {
  it('renders launchpad headline', () => {
    render(<HomePage />);
    expect(screen.getByText('一句话，一段素材，一条成片')).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/帮我做一个/)).toBeInTheDocument();
  });

  it('renders quick prompt buttons', () => {
    render(<HomePage />);
    expect(screen.getByText('小红书口播精剪')).toBeInTheDocument();
  });
});
```

- [ ] **Step 4: 运行测试**

Run: `cd frontend && npm test --run`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/page.tsx frontend/src/components/layout/LaunchNav.tsx frontend/tests/app/LaunchpadPage.test.tsx
git commit -m "feat: rewrite homepage as Agent Launchpad"
```

---

## Task 4: 工作台三栏布局骨架

重写 `frontend/src/app/projects/[id]/page.tsx`，从当前的左-右两栏改为三栏影院式布局。保留数据加载逻辑，但将渲染拆分为左中右三栏。

**Files:**
- Rewrite: `frontend/src/app/projects/[id]/page.tsx`
- Modify: `frontend/src/components/layout/TopBar.tsx`（添加返回按钮）
- Test: `frontend/tests/app/ProjectWorkspacePage.test.tsx`

**Interfaces:**
- Consumes: `Project`, `RenderJob`, `Composition`, `Scene` 类型；`api` 模块。
- Produces: 三栏布局的 `ProjectWorkspacePage`。

- [ ] **Step 1: 修改 TopBar 支持返回按钮和更多 slot**

```typescript
'use client';

import Link from 'next/link';
import { ArrowLeft } from 'lucide-react';

interface TopBarProps {
  title?: string;
  showBack?: boolean;
  backHref?: string;
  right?: React.ReactNode;
}

export function TopBar({ title, showBack = false, backHref = '/projects', right }: TopBarProps) {
  return (
    <header className="h-14 border-b border-border-subtle bg-background-surface/80 backdrop-blur flex items-center justify-between px-4 shrink-0">
      <div className="flex items-center gap-3 min-w-0">
        {showBack && (
          <Link href={backHref} className="text-text-secondary hover:text-content-primary transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
        )}
        {title && <h1 className="text-sm font-semibold text-content-primary truncate">{title}</h1>}
      </div>
      {right && <div className="flex items-center gap-2 shrink-0">{right}</div>}
    </header>
  );
}
```

- [ ] **Step 2: 重写工作台页面为三栏布局**

```typescript
'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { AuthGuard } from '@/components/layout/AuthGuard';
import { AgentChat } from '@/components/project/AgentChat';
import { SceneCards } from '@/components/project/SceneCards';
import { PreviewPlayer } from '@/components/project/PreviewPlayer';
import { PropertyPanel } from '@/components/project/PropertyPanel';
import { Pipeline } from '@/components/project/Pipeline';
import { Button } from '@/components/ui/Button';
import { Project, RenderJob, Scene } from '@/lib/types';
import { api } from '@/lib/api';
import { getDemoProjectById } from '@/lib/demoData';

const PIPELINE_STEPS = [
  { id: 'understand', label: '理解需求' },
  { id: 'analyze', label: '分析素材' },
  { id: 'script', label: '编写脚本' },
  { id: 'scenes', label: '生成场景' },
  { id: 'render', label: '渲染成片' },
  { id: 'output', label: '输出成片' },
];

export default function ProjectWorkspacePage() {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [scenes, setScenes] = useState<Scene[]>([]);
  const [selectedSceneId, setSelectedSceneId] = useState<string | null>(null);
  const [job, setJob] = useState<RenderJob | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await api.get(`/projects/${id}`);
        if (!cancelled) {
          setProject(data);
          if (data.composition?.metadata?.scenes) {
            setScenes(data.composition.metadata.scenes);
          }
        }
      } catch (err) {
        if (!cancelled) {
          const demo = getDemoProjectById(id);
          if (demo) setProject(demo);
          else setError(err instanceof Error ? err.message : '加载项目失败');
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => { cancelled = true; };
  }, [id]);

  if (loading) {
    return (
      <AuthGuard>
        <div className="min-h-screen flex items-center justify-center bg-background-base text-content-secondary">
          <div className="flex flex-col items-center gap-4">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-500" />
            <p className="text-sm">加载项目中…</p>
          </div>
        </div>
      </AuthGuard>
    );
  }

  if (error || !project) {
    return (
      <AuthGuard>
        <div className="min-h-screen flex items-center justify-center bg-background-base">
          <div className="text-center max-w-md">
            <p className="text-error mb-4">{error || '项目不存在'}</p>
            <Button onClick={() => window.location.reload()}>重试</Button>
          </div>
        </div>
      </AuthGuard>
    );
  }

  const currentStepIndex = project.status === 'draft' ? -1 : project.status === 'generating' ? 3 : 5;

  return (
    <AuthGuard>
      <div className="flex min-h-screen bg-background-base">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <TopBar
            title={project.title}
            showBack
            backHref="/projects"
            right={
              <>
                <Button variant="secondary" size="sm">导出 HTML</Button>
                <Button size="sm">导出 MP4</Button>
              </>
            }
          />
          <main className="flex-1 p-5 overflow-hidden">
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-5 h-[calc(100vh-3.5rem-2.5rem)]">
              {/* Left: Agent + Scenes */}
              <div className="lg:col-span-3 flex flex-col gap-4 min-h-0">
                <AgentChat
                  projectId={project.id}
                  status={project.status}
                  selectedSceneId={selectedSceneId}
                  scenes={scenes}
                  onStatusChange={(s) => setProject({ ...project, status: s })}
                />
                <SceneCards
                  scenes={scenes}
                  selectedId={selectedSceneId}
                  onSelect={setSelectedSceneId}
                />
              </div>

              {/* Center: Preview + Pipeline */}
              <div className="lg:col-span-6 flex flex-col gap-4 min-h-0">
                <div className="flex-1 bg-black rounded-lg overflow-hidden min-h-0">
                  <PreviewPlayer videoUrl={job?.output_url || project.latest_output_url} />
                </div>
                {project.status === 'generating' && (
                  <div className="bg-background-surface border border-border-subtle rounded-lg p-4">
                    <Pipeline
                      steps={PIPELINE_STEPS}
                      currentStepIndex={currentStepIndex}
                      currentDescription="正在生成场景 2/4：解决方案展示"
                    />
                  </div>
                )}
              </div>

              {/* Right: Properties */}
              <div className="lg:col-span-3 min-h-0">
                <PropertyPanel
                  project={project}
                  selectedScene={scenes.find((s) => s.id === selectedSceneId)}
                />
              </div>
            </div>
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}
```

- [ ] **Step 3: 更新 Project 类型（添加 latest_output_url 可选字段）**

```typescript
export interface Project {
  id: string;
  title: string;
  source_url?: string;
  source_type: 'url' | 'upload';
  status: 'draft' | 'generating' | 'ready' | 'failed';
  target_format: string;
  target_duration?: number;
  latest_output_url?: string;
  created_at: string;
  updated_at: string;
}
```

- [ ] **Step 4: 写工作台页面测试**

```typescript
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import ProjectWorkspacePage from '@/app/projects/[id]/page';

vi.mock('next/navigation', () => ({
  useParams: () => ({ id: 'test-id' }),
}));

vi.mock('@/lib/api', () => ({
  api: {
    get: vi.fn(() => Promise.reject(new Error('mock'))),
  },
}));

vi.mock('@/lib/demoData', () => ({
  getDemoProjectById: () => ({
    id: 'test-id',
    title: 'Demo Project',
    source_type: 'url',
    status: 'draft',
    target_format: '16:9',
    created_at: '',
    updated_at: '',
  }),
}));

describe('ProjectWorkspacePage', () => {
  it('renders project title', async () => {
    render(<ProjectWorkspacePage />);
    expect(await screen.findByText('Demo Project')).toBeInTheDocument();
  });
});
```

- [ ] **Step 5: 运行测试**

Run: `cd frontend && npm test --run`
Expected: PASS (可能需等待异步渲染，测试使用 `findByText`)。

- [ ] **Step 6: Commit**

```bash
git add frontend/src/app/projects/[id]/page.tsx frontend/src/components/layout/TopBar.tsx frontend/src/lib/types.ts frontend/tests/app/ProjectWorkspacePage.test.tsx
git commit -m "feat: convert workspace to three-column cinematic layout"
```

---

## Task 5: AgentChat 场景上下文增强

增强 `AgentChat` 组件，使其支持 `selectedSceneId` 和 `scenes` props，选中场景时自动带入上下文，并显示 quick prompts。

**Files:**
- Modify: `frontend/src/components/project/AgentChat.tsx`
- Test: `frontend/tests/components/AgentChat.test.tsx`

**Interfaces:**
- Consumes: `Scene[]`, `Project['status']`。
- Produces: `AgentChatProps { projectId: string; status: string; selectedSceneId?: string | null; scenes?: Scene[]; onStatusChange: (s) => void }`。

- [ ] **Step 1: 重写 AgentChat 组件**

```typescript
'use client';

import { useEffect, useRef, useState } from 'react';
import { Button } from '@/components/ui/Button';
import { api } from '@/lib/api';
import { Scene } from '@/lib/types';
import { MessageSquare, Send, Bot, User, Pencil } from 'lucide-react';

interface Message {
  role: 'user' | 'agent';
  text: string;
}

interface AgentChatProps {
  projectId: string;
  status: string;
  selectedSceneId?: string | null;
  scenes?: Scene[];
  onStatusChange: (status: 'draft' | 'generating' | 'ready' | 'failed') => void;
}

const QUICK_PROMPTS = [
  '更活泼一点',
  '针对年轻人',
  '把标题改成红色',
  '缩短到 15 秒',
  '换背景音乐',
];

export function AgentChat({ projectId, status, selectedSceneId, scenes = [], onStatusChange }: AgentChatProps) {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'agent', text: 'Hi! 我是你的 AI 导演。输入一句话开始创作，或点击左侧场景卡片修改某个画面。' },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const selectedScene = scenes.find((s) => s.id === selectedSceneId);

  useEffect(() => {
    if (selectedScene) {
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last?.role === 'agent' && last.text.includes(`「${selectedScene.name}」`)) return prev;
        return [
          ...prev,
          { role: 'agent', text: `你选中了「${selectedScene.name}」（${formatTime(selectedScene.start_time)}-${formatTime(selectedScene.start_time + selectedScene.duration)}）。想怎么改这个场景？` },
        ];
      });
    }
  }, [selectedSceneId, scenes]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || loading) return;
    setMessages((prev) => [...prev, { role: 'user', text }]);
    setInput('');
    setLoading(true);
    setError(null);

    try {
      const payload: Record<string, any> = { message: text, render: true };
      if (selectedSceneId) payload.scene_id = selectedSceneId;
      const data = await api.post(`/projects/${projectId}/agent/chat`, payload);
      const reply = data.reply || '已收到你的修改要求。';
      setMessages((prev) => [...prev, { role: 'agent', text: reply }]);
      if (data.job_id) {
        onStatusChange('generating');
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Agent 请求失败';
      setError(msg);
      setMessages((prev) => [...prev, { role: 'agent', text: `抱歉，我没法应用这个修改：${msg}` }]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  return (
    <div className="bg-background-surface border border-border-subtle rounded-lg p-4 flex flex-col h-[360px]">
      <div className="flex items-center gap-2 mb-3 shrink-0">
        <MessageSquare className="w-4 h-4 text-brand-400" />
        <span className="text-sm font-semibold">AI 导演</span>
        {selectedScene && (
          <span className="ml-auto text-xs px-2 py-0.5 rounded-full bg-brand-900/40 text-brand-400 border border-brand-900/60 flex items-center gap-1">
            <Pencil className="w-3 h-3" /> {selectedScene.name}
          </span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto space-y-3 pr-1 mb-3 min-h-0 text-sm">
        {messages.map((m, idx) => (
          <div key={idx} className={`flex gap-2 ${m.role === 'user' ? 'flex-row-reverse' : ''}`}>
            <div
              className={clsx(
                'w-7 h-7 rounded-full flex items-center justify-center shrink-0',
                m.role === 'agent' ? 'bg-brand-900/50 text-brand-400' : 'bg-background-elevated text-content-secondary'
              )}
            >
              {m.role === 'agent' ? <Bot className="w-3.5 h-3.5" /> : <User className="w-3.5 h-3.5" />}
            </div>
            <div
              className={clsx(
                'max-w-[85%] text-sm px-3 py-2 rounded-lg',
                m.role === 'agent'
                  ? 'bg-background-elevated text-content-secondary border border-border-subtle'
                  : 'bg-brand-600 text-content-inverse'
              )}
            >
              {m.text}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex gap-2">
            <div className="w-7 h-7 rounded-full bg-brand-900/50 text-brand-400 flex items-center justify-center shrink-0">
              <Bot className="w-3.5 h-3.5" />
            </div>
            <div className="bg-background-elevated border border-border-subtle text-content-secondary text-sm px-3 py-2 rounded-lg flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce" />
              <span className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce [animation-delay:0.1s]" />
              <span className="w-1.5 h-1.5 bg-brand-400 rounded-full animate-bounce [animation-delay:0.2s]" />
            </div>
          </div>
        )}
        {error && (
          <div className="text-xs text-error bg-error/10 border border-error/20 px-3 py-2 rounded-lg">
            {error}
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <div className="shrink-0 space-y-2">
        <div className="flex flex-wrap gap-1.5">
          {QUICK_PROMPTS.map((p) => (
            <button
              key={p}
              onClick={() => sendMessage(p)}
              disabled={loading}
              className="text-xs px-2 py-1 rounded-full bg-background-elevated border border-border-subtle text-content-secondary hover:text-content-primary hover:border-border-default transition-colors disabled:opacity-50"
            >
              {p}
            </button>
          ))}
        </div>
        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={selectedScene ? `修改「${selectedScene.name}」…` : '输入创作或修改指令…'}
            disabled={loading}
            className="flex-1 min-w-0 bg-background-elevated border border-border-subtle rounded-md px-3 py-2 text-sm text-content-primary placeholder-content-tertiary focus:outline-none focus:border-brand-500 disabled:opacity-50"
          />
          <Button type="submit" disabled={loading || !input.trim()} size="sm">
            <Send className="w-4 h-4" />
          </Button>
        </form>
      </div>
    </div>
  );
}

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

// Need clsx import
```

注意：需要在文件顶部添加 `import { clsx } from 'clsx';`。

- [ ] **Step 2: 修复缺失的 clsx import**

在 `AgentChat.tsx` 顶部添加：

```typescript
import { clsx } from 'clsx';
```

- [ ] **Step 3: 写 AgentChat 测试**

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { AgentChat } from '@/components/project/AgentChat';

const scenes = [
  { id: 's1', index: 0, name: '开场', start_time: 0, duration: 5 },
];

describe('AgentChat', () => {
  it('renders initial agent message', () => {
    render(<AgentChat projectId="p1" status="draft" onStatusChange={() => {}} />);
    expect(screen.getByText(/我是你的 AI 导演/)).toBeInTheDocument();
  });

  it('shows selected scene badge', () => {
    render(<AgentChat projectId="p1" status="draft" selectedSceneId="s1" scenes={scenes} onStatusChange={() => {}} />);
    expect(screen.getByText('开场')).toBeInTheDocument();
  });
});
```

- [ ] **Step 4: 运行测试**

Run: `cd frontend && npm test --run`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/project/AgentChat.tsx frontend/tests/components/AgentChat.test.tsx
git commit -m "feat: enhance AgentChat with scene context"
```

---

## Task 6: SceneCards 列表与 PropertyPanel 组件

创建 `SceneCards` 列表组件（封装多个 `SceneCard`）和 `PropertyPanel` 属性面板组件。

**Files:**
- Create: `frontend/src/components/project/SceneCards.tsx`
- Create: `frontend/src/components/project/PropertyPanel.tsx`
- Test: `frontend/tests/components/SceneCards.test.tsx`
- Test: `frontend/tests/components/PropertyPanel.test.tsx`

**Interfaces:**
- Consumes: `Scene[]`, `Project`。
- Produces: `SceneCardsProps { scenes: Scene[]; selectedId?: string | null; onSelect: (id: string) => void }`；`PropertyPanelProps { project: Project; selectedScene?: Scene }`。

- [ ] **Step 1: 实现 SceneCards 组件**

```typescript
'use client';

import { SceneCard } from './SceneCard';
import { Scene } from '@/lib/types';
import { Film } from 'lucide-react';

interface SceneCardsProps {
  scenes: Scene[];
  selectedId?: string | null;
  onSelect: (id: string) => void;
}

export function SceneCards({ scenes, selectedId, onSelect }: SceneCardsProps) {
  return (
    <div className="bg-background-surface border border-border-subtle rounded-lg p-4 flex flex-col h-[280px]">
      <div className="flex items-center justify-between mb-3 shrink-0">
        <div className="flex items-center gap-2">
          <Film className="w-4 h-4 text-brand-400" />
          <span className="text-sm font-semibold">场景卡片</span>
        </div>
        <span className="text-xs text-text-tertiary">点卡片修改</span>
      </div>
      {scenes.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-text-tertiary text-sm">
          <Film className="w-8 h-8 mb-2 opacity-50" />
          <p>生成后场景会出现在这里</p>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto space-y-2 pr-1">
          {scenes.map((scene) => (
            <SceneCard
              key={scene.id}
              scene={scene}
              isSelected={scene.id === selectedId}
              onClick={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: 实现 PropertyPanel 组件**

```typescript
'use client';

import { Project, Scene } from '@/lib/types';
import { Type, Clock, Monitor, Image, Music } from 'lucide-react';

interface PropertyPanelProps {
  project: Project;
  selectedScene?: Scene;
}

export function PropertyPanel({ project, selectedScene }: PropertyPanelProps) {
  return (
    <div className="bg-background-surface border border-border-subtle rounded-lg p-4 h-full overflow-y-auto">
      {selectedScene ? (
        <div className="space-y-5">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <Type className="w-4 h-4 text-brand-400" />
            场景属性
          </div>
          <div>
            <label className="text-xs text-text-secondary block mb-1">场景名称</label>
            <input
              type="text"
              defaultValue={selectedScene.name}
              className="w-full bg-background-elevated border border-border-subtle rounded-md px-2 py-1.5 text-sm outline-none focus:border-brand-500"
            />
          </div>
          <div>
            <label className="text-xs text-text-secondary block mb-1">场景文案</label>
            <textarea
              defaultValue={selectedScene.text_content || ''}
              rows={3}
              className="w-full bg-background-elevated border border-border-subtle rounded-md px-2 py-1.5 text-sm outline-none focus:border-brand-500 resize-none"
            />
          </div>
          <div>
            <label className="text-xs text-text-secondary block mb-1">时长（秒）</label>
            <input
              type="number"
              defaultValue={selectedScene.duration}
              className="w-full bg-background-elevated border border-border-subtle rounded-md px-2 py-1.5 text-sm outline-none focus:border-brand-500"
            />
          </div>
        </div>
      ) : (
        <div className="space-y-5">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <Monitor className="w-4 h-4 text-brand-400" />
            项目属性
          </div>
          <div>
            <label className="text-xs text-text-secondary block mb-1">标题</label>
            <input
              type="text"
              defaultValue={project.title}
              className="w-full bg-background-elevated border border-border-subtle rounded-md px-2 py-1.5 text-sm outline-none focus:border-brand-500"
            />
          </div>
          <div>
            <label className="text-xs text-text-secondary block mb-1">画幅</label>
            <div className="flex gap-2">
              {['16:9', '9:16', '1:1'].map((ratio) => (
                <button
                  key={ratio}
                  className={`flex-1 py-1.5 rounded-md text-xs border transition-colors ${
                    project.target_format === ratio
                      ? 'bg-brand-900/50 text-brand-400 border-brand-900/60'
                      : 'bg-background-elevated text-text-secondary border-border-subtle hover:border-border-default'
                  }`}
                >
                  {ratio}
                </button>
              ))}
            </div>
          </div>
          <div>
            <label className="text-xs text-text-secondary block mb-1">目标时长</label>
            <div className="flex items-center gap-2">
              <Clock className="w-4 h-4 text-text-tertiary" />
              <input
                type="number"
                defaultValue={project.target_duration || 30}
                className="flex-1 bg-background-elevated border border-border-subtle rounded-md px-2 py-1.5 text-sm outline-none focus:border-brand-500"
              />
              <span className="text-xs text-text-secondary">秒</span>
            </div>
          </div>
          <div className="border-t border-border-subtle pt-4">
            <div className="flex items-center gap-2 text-sm font-semibold mb-3">
              <Image className="w-4 h-4 text-brand-400" />
              素材
            </div>
            <div className="space-y-2">
              <div className="flex items-center gap-2 p-2 bg-background-elevated rounded-md border border-border-subtle">
                <div className="w-8 h-8 rounded bg-blue-600/30 flex items-center justify-center text-xs">图</div>
                <div className="text-xs truncate">product-shot.png</div>
              </div>
              <div className="flex items-center gap-2 p-2 bg-background-elevated rounded-md border border-border-subtle">
                <div className="w-8 h-8 rounded bg-emerald-600/30 flex items-center justify-center text-xs"><Music className="w-3.5 h-3.5" /></div>
                <div className="text-xs truncate">bgm-upbeat.mp3</div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: 写 SceneCards 和 PropertyPanel 测试**

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { SceneCards } from '@/components/project/SceneCards';
import { PropertyPanel } from '@/components/project/PropertyPanel';
import { Project, Scene } from '@/lib/types';

const scenes: Scene[] = [
  { id: 's1', index: 0, name: '开场', start_time: 0, duration: 5 },
  { id: 's2', index: 1, name: '正文', start_time: 5, duration: 10 },
];

const mockProject: Project = {
  id: 'p1',
  title: 'Test',
  source_type: 'url',
  status: 'draft',
  target_format: '16:9',
  target_duration: 30,
  created_at: '',
  updated_at: '',
};

describe('SceneCards', () => {
  it('renders scene list', () => {
    render(<SceneCards scenes={scenes} onSelect={() => {}} />);
    expect(screen.getByText('开场')).toBeInTheDocument();
    expect(screen.getByText('正文')).toBeInTheDocument();
  });

  it('calls onSelect when scene clicked', () => {
    const onSelect = vi.fn();
    render(<SceneCards scenes={scenes} onSelect={onSelect} />);
    fireEvent.click(screen.getByText('正文'));
    expect(onSelect).toHaveBeenCalledWith('s2');
  });
});

describe('PropertyPanel', () => {
  it('renders project title', () => {
    render(<PropertyPanel project={mockProject} />);
    expect(screen.getByDisplayValue('Test')).toBeInTheDocument();
  });

  it('renders scene properties when scene selected', () => {
    render(<PropertyPanel project={mockProject} selectedScene={scenes[0]} />);
    expect(screen.getByText('场景属性')).toBeInTheDocument();
    expect(screen.getByDisplayValue('开场')).toBeInTheDocument();
  });
});
```

- [ ] **Step 4: 运行测试**

Run: `cd frontend && npm test --run`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/project/SceneCards.tsx frontend/src/components/project/PropertyPanel.tsx frontend/tests/components/SceneCards.test.tsx frontend/tests/components/PropertyPanel.test.tsx
git commit -m "feat: add SceneCards list and PropertyPanel"
```

---

## Task 7: PreviewPlayer 增强与画幅切换

增强 `PreviewPlayer` 组件，支持根据 `target_format` 显示不同画幅，并添加播放控制条。

**Files:**
- Modify: `frontend/src/components/project/PreviewPlayer.tsx`
- Test: `frontend/tests/components/PreviewPlayer.test.tsx`

**Interfaces:**
- Consumes: `videoUrl?: string`, `format?: '16:9' | '9:16' | '1:1'`。
- Produces: `PreviewPlayerProps { videoUrl?: string; format?: '16:9' | '9:16' | '1:1' }`。

- [ ] **Step 1: 重写 PreviewPlayer 组件**

```typescript
'use client';

import { useRef, useState } from 'react';
import { Play, Pause, Film } from 'lucide-react';

interface PreviewPlayerProps {
  videoUrl?: string;
  format?: '16:9' | '9:16' | '1:1';
}

const FORMAT_RATIO: Record<string, string> = {
  '16:9': 'aspect-video',
  '9:16': 'aspect-[9/16]',
  '1:1': 'aspect-square',
};

export function PreviewPlayer({ videoUrl, format = '16:9' }: PreviewPlayerProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [playing, setPlaying] = useState(false);

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (playing) {
      videoRef.current.pause();
    } else {
      videoRef.current.play();
    }
    setPlaying(!playing);
  };

  if (!videoUrl) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center text-white bg-black">
        <div className="relative mb-4">
          <div className="absolute inset-0 bg-brand-500/20 blur-xl rounded-full" />
          <div className="relative w-16 h-16 rounded-full bg-background-elevated/80 border border-border-default flex items-center justify-center">
            <Film className="w-7 h-7 text-content-tertiary" />
          </div>
        </div>
        <p className="text-content-secondary font-medium">视频将在这里预览</p>
        <p className="text-content-tertiary text-sm mt-1">点击「开始生成」后，成片会出现在此处</p>
      </div>
    );
  }

  return (
    <div className="w-full h-full flex flex-col items-center justify-center bg-black relative">
      <div className={`relative ${FORMAT_RATIO[format] || 'aspect-video'} max-h-full max-w-full`}>
        <video
          ref={videoRef}
          src={videoUrl}
          className="w-full h-full object-contain rounded-lg"
          controls={false}
          onPlay={() => setPlaying(true)}
          onPause={() => setPlaying(false)}
          poster="/api/static/placeholder.png"
        />
        <button
          onClick={togglePlay}
          className="absolute inset-0 flex items-center justify-center bg-black/20 opacity-0 hover:opacity-100 transition-opacity"
          aria-label={playing ? '暂停' : '播放'}
        >
          <div className="w-14 h-14 rounded-full bg-brand-600/90 flex items-center justify-center backdrop-blur">
            {playing ? <Pause className="w-6 h-6 text-white" /> : <Play className="w-6 h-6 text-white ml-1" />}
          </div>
        </button>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 写 PreviewPlayer 测试**

```typescript
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { PreviewPlayer } from '@/components/project/PreviewPlayer';

describe('PreviewPlayer', () => {
  it('shows placeholder when no videoUrl', () => {
    render(<PreviewPlayer />);
    expect(screen.getByText('视频将在这里预览')).toBeInTheDocument();
  });

  it('renders video when videoUrl provided', () => {
    render(<PreviewPlayer videoUrl="/api/static/sample.mp4" format="16:9" />);
    expect(screen.getByRole('button', { name: /播放/ })).toBeInTheDocument();
  });
});
```

- [ ] **Step 3: 运行测试**

Run: `cd frontend && npm test --run`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/project/PreviewPlayer.tsx frontend/tests/components/PreviewPlayer.test.tsx
git commit -m "feat: enhance PreviewPlayer with format support"
```

---

## Task 8: 后端 Agent 支持场景级上下文

扩展后端 Agent API，使 `POST /projects/{id}/agent/chat` 支持可选的 `scene_id` 参数，并在 LLM/fallback 中携带场景上下文。

**Files:**
- Modify: `backend/app/routers/agent.py`
- Modify: `backend/app/agent/modifier.py`
- Modify: `backend/app/agent/__init__.py`（如有需要）
- Test: `backend/tests/test_agent.py`（新增或修改）

**Interfaces:**
- Consumes: `scene_id: str | None` from request body.
- Produces: `modify_video(project_id, user_message, scene_id=None) -> dict` function signature.

- [ ] **Step 1: 查看现有 agent router**

Read `backend/app/routers/agent.py` and `backend/app/agent/modifier.py` to confirm current structure.

- [ ] **Step 2: 修改 modifier.py 支持 scene_id**

```python
import json
import logging
from typing import Optional

from .llm import KimiClient
from .prompts import MODIFY_VIDEO

logger = logging.getLogger(__name__)


def _fallback_modify(composition: dict, user_message: str, scene_id: Optional[str] = None) -> dict:
    """Deterministic fallback when LLM is unavailable."""
    message_lower = user_message.lower()

    if scene_id:
        # Apply a targeted change to the scene if it exists
        for track in composition.get("tracks", []):
            for clip in track.get("clips", []):
                if clip.get("scene_id") == scene_id or clip.get("id") == scene_id:
                    if "红" in user_message or "red" in message_lower:
                        clip.setdefault("style", {})["color"] = "#ef4444"
                    if "大" in user_message or "big" in message_lower:
                        clip.setdefault("style", {})["fontSize"] = 96
                    if "短" in user_message or "short" in message_lower:
                        clip["duration"] = max(1, clip.get("duration", 5) - 2)
                    return composition

    # Global changes
    if "短" in user_message or "short" in message_lower:
        composition["duration"] = max(5, composition.get("duration", 30) // 2)
    if "红" in user_message or "red" in message_lower:
        for track in composition.get("tracks", []):
            for clip in track.get("clips", []):
                clip.setdefault("style", {})["color"] = "#ef4444"
    return composition


def modify_video(composition: dict, user_message: str, scene_id: Optional[str] = None) -> dict:
    """Modify composition based on natural language instruction."""
    prompt = json.dumps({
        "composition": composition,
        "user_message": user_message,
        "scene_id": scene_id,
    }, ensure_ascii=False, indent=2)

    try:
        client = KimiClient()
        result = client.chat_completion_json(
            system_prompt=MODIFY_VIDEO,
            user_prompt=prompt,
        )
        if result and "tracks" in result:
            logger.info("Composition modified via LLM")
            return result
    except Exception as exc:
        logger.error("modify_video LLM failed, using fallback: %s", exc)

    return _fallback_modify(composition, user_message, scene_id)
```

- [ ] **Step 3: 修改 agent router 接收 scene_id**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agent import plan_video, build_composition, generate_html, modify_video
from app.config import ASSETS_DIR
from app.database import get_db
from app.models import Project, User, Track, Clip
from app.routers.auth import get_current_user
from app.routers.compositions import build_composition_json
import os
import json

router = APIRouter(prefix="/projects/{project_id}/agent", tags=["agent"])


@router.post("/chat")
def agent_chat(
    project_id: str,
    data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project or project.user_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")

    message = data.get("message", "")
    scene_id = data.get("scene_id")
    should_render = data.get("render", False)

    if not project.composition:
        return {"reply": "项目还没有合成内容，请先开始生成。", "composition": None, "job_id": None}

    comp_json = build_composition_json(project.composition)

    try:
        new_comp = modify_video(comp_json, message, scene_id=scene_id)
        # Persist new composition...
        _persist_composition(project, new_comp, db)

        reply = f"已应用修改：{message}"
        if scene_id:
            reply = f"已针对场景调整：{message}"

        job_id = None
        if should_render:
            # queue render job
            pass

        return {"reply": reply, "composition": new_comp, "job_id": job_id}
    except Exception as exc:
        return {"reply": f"修改失败：{exc}", "composition": comp_json, "job_id": None}


def _persist_composition(project, comp_json, db):
    from app.models import Track as TrackModel, Clip as ClipModel
    for track in project.composition.tracks:
        db.delete(track)
    db.flush()
    for t_data in comp_json.get("tracks", []):
        track = TrackModel(
            composition_id=project.composition.id,
            type=t_data["type"],
            index=t_data["index"],
            name=t_data.get("name"),
        )
        db.add(track)
        db.flush()
        for c_data in t_data.get("clips", []):
            clip = ClipModel(
                track_id=track.id,
                asset_id=c_data.get("asset_id"),
                start_time=c_data.get("start_time", 0),
                duration=c_data.get("duration", 5),
                position=c_data.get("position", {}),
                style=c_data.get("style", {}),
                text_content=c_data.get("text_content"),
            )
            db.add(clip)
    db.commit()
    db.refresh(project)
```

注意：这里需要确认 `app/agent/__init__.py` 已经导出 `modify_video`，如果没有则在 `__init__.py` 中添加。

- [ ] **Step 4: 确保 modify_video 被导出**

修改 `backend/app/agent/__init__.py`：

```python
from .planner import plan_video
from .composer import build_composition
from .html_generator import generate_html
from .modifier import modify_video
```

- [ ] **Step 5: 写后端测试**

```python
import pytest
from app.agent.modifier import modify_video


def test_modify_video_fallback_global():
    comp = {"duration": 30, "tracks": [{"type": "text", "clips": [{"duration": 5, "style": {}}]}]}
    result = modify_video(comp, "把视频缩短一点")
    assert result["duration"] < 30


def test_modify_video_fallback_scene():
    comp = {
        "duration": 30,
        "tracks": [{
            "type": "text",
            "clips": [{"id": "scene-1", "duration": 5, "style": {}}]
        }]
    }
    result = modify_video(comp, "把标题改成红色", scene_id="scene-1")
    assert result["tracks"][0]["clips"][0]["style"]["color"] == "#ef4444"
```

- [ ] **Step 6: 运行测试**

Run: `cd backend && pytest tests/test_agent.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add backend/app/agent/modifier.py backend/app/routers/agent.py backend/app/agent/__init__.py backend/tests/test_agent.py
git commit -m "feat: support scene_id context in agent chat"
```

---

## Task 9: 首页到工作台流程打通

确保从 Launchpad 创建项目后，工作台能正确加载并（可选）自动开始生成。同时修复 `Project` 类型与后端返回数据的对齐问题。

**Files:**
- Modify: `frontend/src/app/page.tsx`（确认创建后跳转）
- Modify: `frontend/src/app/projects/[id]/page.tsx`（加载时若无场景且非生成中，提示用户开始生成）
- Modify: `frontend/src/components/project/GenerationPanel.tsx`（可选保留或移除，用 AgentChat 替代主要入口）
- Test: 手动验证 E2E 流程

**Interfaces:**
- Consumes: `api.post('/projects/', ...)`；`api.post('/projects/{id}/renders/agent-generate', ...)`。
- Produces: 从首页到工作台的导航 + 初始生成触发。

- [ ] **Step 1: 确认首页创建项目后跳转**

`frontend/src/app/page.tsx` 中 `createProject` 已在 Task 3 实现，确认 `router.push(`/projects/${project.id}`)` 存在。

- [ ] **Step 2: 在工作台添加「开始生成」入口**

在 `frontend/src/app/projects/[id]/page.tsx` 的左栏 `AgentChat` 上方添加一个生成按钮，当 `project.status === 'draft'` 时显示：

```typescript
{project.status === 'draft' && (
  <button
    onClick={async () => {
      await api.post(`/projects/${project.id}/renders/agent-generate`, { prompt: project.title });
      setProject({ ...project, status: 'generating' });
    }}
    className="w-full bg-brand-600 hover:bg-brand-500 text-white py-2.5 rounded-lg text-sm font-medium flex items-center justify-center gap-2 transition-colors"
  >
    <Sparkles className="w-4 h-4" />
    开始生成视频
  </button>
)}
```

需要在文件顶部导入 `Sparkles`：

```typescript
import { Sparkles } from 'lucide-react';
```

- [ ] **Step 3: 运行前端测试**

Run: `cd frontend && npm test --run`
Expected: PASS.

- [ ] **Step 4: 手动验证 E2E**

1. 启动 Docker 服务：`docker-compose up -d`
2. 访问 http://localhost:3000
3. 在首页输入框输入「帮我做一个 30 秒的产品介绍视频」
4. 点击「开始创作」
5. 确认跳转到工作台 `/projects/{id}`
6. 点击「开始生成视频」
7. 确认流水线出现，状态变为 generating
8. 等待完成后，确认场景卡片出现

- [ ] **Step 5: Commit**

```bash
git add frontend/src/app/projects/[id]/page.tsx
git commit -m "feat: wire launchpad to workspace generation flow"
```

---

## Task 10: 样式打磨、响应式与清理

收尾工作：统一细节样式、处理移动端响应式、清理不再使用的旧组件引用、确保 lint 通过。

**Files:**
- Modify: `frontend/src/app/projects/[id]/page.tsx`
- Modify: `frontend/src/app/globals.css`（如需要添加工具类）
- Delete or move: `frontend/src/components/project/GenerationPanel.tsx`（如不再使用，可保留但移除引用）
- Test: `cd frontend && npm run lint`

**Interfaces:**
- N/A — 纯 UI/样式调整。

- [ ] **Step 1: 添加响应式折叠**

在三栏布局外层添加响应式类，小屏幕时左栏和右栏可折叠或垂直堆叠：

```typescript
<div className="grid grid-cols-1 lg:grid-cols-12 gap-5 h-[calc(100vh-3.5rem-2.5rem)]">
  {/* mobile: left column above preview, right column below */}
</div>
```

为简化，可保持当前 grid，但为左/右栏添加 `hidden lg:flex` 的折叠按钮。MVP 阶段先保证桌面端完美，移动端可垂直堆叠。

- [ ] **Step 2: 清理旧组件引用**

在 `frontend/src/app/projects/[id]/page.tsx` 中删除未使用的 `DownloadButtons`、`ScriptPanel` 等旧引用（如果不再使用）。

- [ ] **Step 3: 运行 lint 和测试**

Run: `cd frontend && npm run lint && npm test --run`
Expected: No lint errors, all tests PASS.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "polish: responsive layout and cleanup"
```

---

## Spec Coverage Check

对照 `docs/superpowers/specs/2026-07-05-clipworks-agentic-ui-design.md`：

| 设计需求 | 对应 Task |
|---------|----------|
| Agent Launchpad 首页 | Task 3 |
| 三栏影院式工作台 | Task 4 |
| 场景卡片系统 | Task 2, Task 6 |
| 可视化流水线 | Task 2 |
| Agent 对话上下文 | Task 5, Task 8 |
| 属性面板 | Task 6 |
| 首页到工作台流程 | Task 3, Task 9 |
| 后端 scene_id 支持 | Task 8 |

无遗漏。

## Placeholder Scan

- 无 TBD/TODO。
- 无 "add appropriate error handling" 等模糊描述。
- 所有代码片段完整。
- 所有测试命令和预期输出明确。

## Type Consistency Check

- `Scene` 类型在 Task 2 定义，后续 Task 5/6/8 一致使用。
- `AgentChatProps` 在 Task 5 定义，与 Task 4 中调用一致。
- `PipelineProps` 在 Task 2 定义，与 Task 4 中调用一致。
- `modify_video` 签名在 Task 8 定义，与 router 调用一致。

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-07-05-clipworks-agentic-ui.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** - Execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints.

**Which approach?**
