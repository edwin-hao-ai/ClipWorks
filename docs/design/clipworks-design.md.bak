# ClipWorks（映工厂）Design System

> A design.md for the AI video factory.  
> This document is the single source of truth for brand, visuals, components, motion, and demo data. Every screen in ClipWorks should be derivable from this file.

---

## 1. Brand Identity

### 1.1 Name & Tagline

- **EN**: ClipWorks
- **CN**: 映工厂
- **Tagline**: "AI 驱动的视频生成与剪辑工具"
- **Short pitch**: 一句话，一段素材，一条成片。

### 1.2 Personality

- **Friendly but capable** — 小白能上手，专业用户不觉得幼稚。
- **Fast and fluid** — 视频是时间艺术，界面要让人感受到“快”。
- **Clean and cinematic** — 像剪辑软件的暗色工作台，但不压抑。

### 1.3 Visual Metaphor

- 工厂 / 流水线：输入 → 加工 → 出片。
- 胶片 / 时间线：剪辑的核心符号。
- 魔法 / 星星：AI 一键生成的惊喜感（克制使用，不要过度）。

---

## 2. Color Palette

### 2.1 Primitives

| Token | Hex | Usage |
|-------|-----|-------|
| `--brand-50` | `#f0f9ff` | Hover backgrounds, light tints |
| `--brand-100` | `#e0f2fe` | Selected states, subtle highlights |
| `--brand-200` | `#bae6fd` | Borders, dividers |
| `--brand-400` | `#38bdf8` | Secondary accents |
| `--brand-500` | `#0ea5e9` | Primary brand color (sky blue) |
| `--brand-600` | `#0284c7` | Primary buttons, links |
| `--brand-700` | `#0369a1` | Active/pressed states |
| `--brand-900` | `#0c4a6e` | Strong emphasis text |

### 2.2 Neutrals (Dark Mode First)

ClipWorks is a **dark-first** app. The workspace should feel like a cinema / editing suite.

| Token | Hex | Usage |
|-------|-----|-------|
| `--bg-base` | `#0a0a0f` | Deepest background |
| `--bg-surface` | `#13131a` | Cards, panels |
| `--bg-elevated` | `#1c1c27` | Elevated cards, modals |
| `--bg-hover` | `#252532` | Hover states |
| `--border-subtle` | `#27273a` | Subtle dividers |
| `--border-default` | `#3f3f5a` | Default borders |
| `--text-primary` | `#f8fafc` | Headings, primary text |
| `--text-secondary` | `#94a3b8` | Body text, labels |
| `--text-tertiary` | `#64748b` | Placeholders, disabled |
| `--text-inverse` | `#0a0a0f` | Text on light/brand backgrounds |

### 2.3 Semantic Colors

| Token | Hex | Usage |
|-------|-----|-------|
| `--success` | `#22c55e` | Ready, completed, success |
| `--warning` | `#f59e0b` | Generating, processing, caution |
| `--error` | `#ef4444` | Failed, error, delete |
| `--info` | `#0ea5e9` | Info, tips |

### 2.4 Timeline Colors

| Track Type | Color |
|------------|-------|
| Video | `--brand-500` |
| Image | `#8b5cf6` (violet) |
| Audio | `#10b981` (emerald) |
| Text / Subtitle | `#f59e0b` (amber) |
| Effect / Overlay | `#ec4899` (pink) |

---

## 3. Typography

### 3.1 Font Stack

- **Primary**: `"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif`
- **Mono**: `"JetBrains Mono", "Fira Code", monospace` — for timestamps, code, technical labels
- **Display**: `"Inter"` with tight tracking for large headlines

### 3.2 Type Scale

| Style | Size | Weight | Line Height | Usage |
|-------|------|--------|-------------|-------|
| Display | 48px | 700 | 1.1 | Marketing hero |
| H1 | 32px | 700 | 1.2 | Page title |
| H2 | 24px | 600 | 1.3 | Section title |
| H3 | 18px | 600 | 1.4 | Card title |
| Body | 14px | 400 | 1.5 | Body text |
| Body-small | 13px | 400 | 1.5 | Secondary text |
| Caption | 12px | 500 | 1.4 | Labels, timestamps |
| Button | 14px | 500 | 1 | Buttons |

### 3.3 Chinese Considerations

- 中文标题使用正常字重（不要过细），最小 font-weight 400。
- 行高适当增加：中文正文行高 1.6-1.8。
- 段落宽度控制在 25-35 个中文字符。

---

## 4. Spacing & Layout

### 4.1 Spacing Scale

| Token | Value |
|-------|-------|
| `--space-1` | 4px |
| `--space-2` | 8px |
| `--space-3` | 12px |
| `--space-4` | 16px |
| `--space-5` | 20px |
| `--space-6` | 24px |
| `--space-8` | 32px |
| `--space-10` | 40px |
| `--space-12` | 48px |
| `--space-16` | 64px |

### 4.2 Layout Grid

- Workspace uses a **12-column grid** inside the main content area.
- Sidebar is fixed `240px`.
- TopBar is fixed `56px`.
- Main content has `24px` padding.
- Cards use `16px` padding and `12px` gap.

### 4.3 Radius

| Token | Value | Usage |
|-------|-------|-------|
| `--radius-sm` | 6px | Buttons, inputs, small elements |
| `--radius-md` | 10px | Cards, panels |
| `--radius-lg` | 16px | Modals, large cards |
| `--radius-xl` | 24px | Hero cards, feature cards |
| `--radius-full` | 9999px | Pills, avatars |

### 4.4 Shadows

| Token | Value | Usage |
|-------|-------|-------|
| `--shadow-sm` | `0 1px 2px rgba(0,0,0,0.3)` | Buttons, inputs |
| `--shadow-md` | `0 4px 12px rgba(0,0,0,0.4)` | Cards, dropdowns |
| `--shadow-lg` | `0 12px 32px rgba(0,0,0,0.5)` | Modals, popovers |
| `--shadow-glow` | `0 0 24px rgba(14,165,233,0.25)` | Brand glow on CTAs |

---

## 5. Components

### 5.1 Button

**Primary Button**
- Background: `--brand-600`
- Text: `--text-inverse`
- Padding: `10px 16px`
- Radius: `--radius-sm`
- Hover: `--brand-500` + `--shadow-glow`
- Active: `--brand-700`
- Disabled: opacity 0.5, cursor not-allowed

**Secondary Button**
- Background: `--bg-elevated`
- Border: 1px solid `--border-default`
- Text: `--text-primary`
- Hover: `--bg-hover`

**Ghost Button**
- Background: transparent
- Text: `--text-secondary`
- Hover: `--bg-hover`

### 5.2 Card

- Background: `--bg-surface`
- Border: 1px solid `--border-subtle`
- Radius: `--radius-md`
- Padding: `--space-4`
- Hover: border transitions to `--border-default`, subtle lift

### 5.3 Input

- Background: `--bg-elevated`
- Border: 1px solid `--border-default`
- Radius: `--radius-sm`
- Padding: `10px 12px`
- Placeholder: `--text-tertiary`
- Focus: border `--brand-500`, ring `0 0 0 2px rgba(14,165,233,0.2)`

### 5.4 Modal / Dialog

- Overlay: `rgba(0,0,0,0.7)` with backdrop-blur
- Panel: `--bg-elevated`
- Radius: `--radius-lg`
- Shadow: `--shadow-lg`
- Max-width: `520px`

### 5.5 Badge / Status Pill

| Status | Background | Text |
|--------|-----------|------|
| Draft | `--bg-hover` | `--text-secondary` |
| Generating | `rgba(245,158,11,0.15)` | `--warning` |
| Ready | `rgba(34,197,94,0.15)` | `--success` |
| Failed | `rgba(239,68,68,0.15)` | `--error` |

### 5.6 Sidebar

- Width: `240px`
- Background: `--bg-surface`
- Border-right: 1px solid `--border-subtle`
- Active item: `--brand-900` background, `--brand-400` text, left `3px` brand border
- Inactive item: `--text-secondary`, hover `--bg-hover`

### 5.7 TopBar

- Height: `56px`
- Background: `--bg-surface` with `backdrop-blur`
- Border-bottom: 1px solid `--border-subtle`
- Contains: page title, user avatar, actions

### 5.8 Timeline

- Background: `--bg-surface`
- Track height: `48px`
- Clip radius: `--radius-sm`
- Playhead: `--error` red line with white triangle handle
- Ruler: `--text-tertiary` ticks on `--bg-base`

---

## 6. Page Specifications

### 6.1 Login Page

**Layout**: Centered card on a dark gradient background.
**Background**:
- Base: `--bg-base`
- Gradient overlay: radial gradient from `--brand-900` at 20% opacity in top-left to transparent
- Subtle grid pattern overlay at 5% opacity

**Card**:
- Width: `420px`
- Background: `--bg-surface` with 80% opacity + `backdrop-blur(12px)`
- Border: 1px solid `--border-default`
- Shadow: `--shadow-lg`

**Content**:
- Logo + name at top
- Tagline below
- Two large buttons: "使用 Google 登录" / "使用 GitHub 登录"
- Subtle footer: "ClipWorks 映工厂 · AI 视频工厂"

### 6.2 Projects List

**Layout**: Sidebar + main content grid.
**Header**: "我的项目" + "新建项目" primary button.
**Empty state**: Large film icon + "开始你的第一个视频项目" + CTA.
**Project cards**:
- 16:9 thumbnail placeholder with gradient
- Title, source URL
- Status pill
- Format badge (16:9 / 9:16 / 1:1)
- Duration
- Hover: play icon overlay + lift

### 6.3 Project Workspace

**Layout**:
- Left panel (320px): generation controls + script outline + quick links
- Center: video preview (16:9 black canvas)
- Right panel (optional, 280px): properties

**Generation panel**:
- Large CTA button "开始生成"
- Progress bar with percentage
- Status pill

**Preview area**:
- Dark canvas with centered video
- When empty: animated placeholder + "视频将在这里预览"
- When ready: video player + download buttons

### 6.4 Timeline Editor

**Layout**:
- Top: preview player
- Bottom: timeline panel

**Timeline panel**:
- Header with time display + zoom controls
- Ruler
- Track list with icons
- Clips as rounded blocks

### 6.5 Assets Library

**Layout**: Sidebar + main grid.
**Header**: "素材库" + upload button.
**Grid**: masonry or uniform cards.
**Asset card**: thumbnail/icon + filename + type badge.
**Upload zone**: dashed border drop area.

### 6.6 Settings / Billing

Placeholder pages but should match the visual system.

---

## 7. Motion & Animation

### 7.1 Principles

- **Snappy**: most transitions 150-250ms
- **Purposeful**: motion should guide attention, not decorate
- **Cinematic previews**: video-related transitions can be slightly longer (300-400ms)

### 7.2 Durations

| Type | Duration | Easing |
|------|----------|--------|
| Button hover | 150ms | ease-out |
| Card hover lift | 200ms | cubic-bezier(0.4, 0, 0.2, 1) |
| Modal open | 250ms | cubic-bezier(0.16, 1, 0.3, 1) |
| Page transition | 200ms | ease-in-out |
| Progress bar | 300ms | ease-out |
| Skeleton shimmer | 1.5s | linear infinite |

### 7.3 Key Animations

- **Generating pulse**: a soft brand glow pulses on the generate button while processing.
- **Progress bar**: fill with a subtle shimmer.
- **Card hover**: translateY(-2px) + shadow deepen.
- **Modal**: scale from 0.96 + opacity fade in.
- **Skeleton**: shimmer gradient sweep.

---

## 8. Demo Data

For prototype/demo purposes, seed the following sample data so screens never look empty.

### 8.1 Demo User

```json
{
  "name": "Demo Creator",
  "email": "demo@clipworks.io",
  "avatar_url": "https://api.dicebear.com/7.x/avataaars/svg?seed=ClipWorks"
}
```

### 8.2 Demo Projects (3)

1. **SaaS 产品发布视频**
   - Source: https://clipworks.io
   - Status: ready
   - Format: 16:9
   - Duration: 45s
   - Thumbnail gradient: blue → purple

2. **小红书口播精剪**
   - Source: upload
   - Status: ready
   - Format: 9:16
   - Duration: 32s
   - Thumbnail gradient: pink → orange

3. **功能更新说明**
   - Source: https://docs.clipworks.io
   - Status: draft
   - Format: 16:9
   - Duration: 60s
   - Thumbnail gradient: green → teal

### 8.3 Demo Script Outline

For any generated project, show:

```
钩子：还在手动做产品视频？试试 ClipWorks，一键生成。
场景 1：展示产品首页截图，突出核心卖点。
场景 2：用户痛点 + 解决方案动画。
场景 3：真实用户证言/数据展示。
结尾：行动号召，访问官网。
```

### 8.4 Demo Assets (5)

- Logo (SVG)
- Product screenshot 1
- Product screenshot 2
- Background music (audio icon)
- Voiceover sample (audio icon)

---

## 9. Implementation Notes

- Use Tailwind CSS for styling.
- Define design tokens as CSS variables in `globals.css` or Tailwind config.
- Use `clsx` + `tailwind-merge` for conditional classes.
- Keep components dark-mode by default; do not implement light mode for MVP.
- Demo data can be hard-coded in frontend or served from a `/demo/seed` endpoint.
- Agent logic remains mocked; focus on visual completeness and demo flow.
