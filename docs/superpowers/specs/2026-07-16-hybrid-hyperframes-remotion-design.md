# ClipWorks Hybrid 渲染设计：HyperFrames 场景预渲染 + Remotion 总装

> 日期：2026-07-16
> 状态：已确认，待实施
> 目标：每个视频场景同时利用 HyperFrames 的 HTML/CSS 动效表现力与 Remotion 的时间线、转场、音轨合成能力，输出专业级成片。

## 1. 背景与问题

当前 ClipWorks 的渲染层有两个互斥的后端：

- **HyperFrames**：把整片 composition 渲染成一个自包含 HTML，再由 HyperFrames CLI 输出 MP4。优势是复杂 CSS/HTML 动效自由度高；劣势是音轨、精确转场、素材代理、多轨合成能力弱。
- **Remotion**：把 composition 渲染成帧序列，支持精确时间线、转场、字幕、角标、音轨混音。优势是整片专业度高；劣势是复杂 HTML/CSS 动效需要手写 React/Canvas，表现力不如直接写 CSS。

用户希望“每个场景都要有 HyperFrame 和 Remotion 一起，把 HTML 做得很漂亮、动效做好”。即：单镜视觉表现交给 HyperFrames，整片结构、转场、音轨交给 Remotion。

## 2. 目标

- 默认渲染路径变为 **hybrid**：HyperFrames 预渲染每个 scene 的画面动画，Remotion 负责总装。
- 单 scene 失败不整片失败，自动回退到 Remotion 内置动效。
- 保持或提升成片专业度：统一视觉风格、流畅动效曲线、清晰文字可读性、准确音画同步。
- 提供场景级进度反馈与可复用缓存，改善用户体验。

## 3. 非目标

- 不替换 `video-use` 引擎；原始视频素材剪辑仍走 `video-use`。
- 不在本方案中实现透明通道的 HTML overlay 层（路线 B），避免 Chromium/MP4 透明视频复杂度。
- 不引入新的前端页面；仅通过现有 `RenderJob.logs` 与素材库暴露 scene 预览。

## 4. 整体架构

### 4.1 数据流

1. Agent 产出 `plan`（含 `scenes` 数组）。
2. `composer.build_composition(plan)` 生成 `composition`。
3. `render_task` 从 `composition.metadata.plan.scenes` 拆出 scene 列表。
4. 对每个 scene：
   - `html_generator.generate_scene_html(scene, composition, assets)` 生成独立 HTML。
   - POST `/render/hyperframes` 渲染成 `scene_{i}.mp4`。
5. 用 `scene_{i}.mp4` 组装新的“总装 composition”：
   - 每个 scene 对应一个 `video` 轨 clip，引用 `scene_{i}.mp4`。
   - 保留 text/overlay 轨给 Remotion 做字幕、角标。
   - 保留 transition 字段，让 Remotion 在 scene 片段之间做转场。
6. Remotion 渲染总装 composition → `/render/mux-audio` 混入音轨 → 最终 MP4。

### 4.2 模块职责

| 模块 | 职责 |
|---|---|
| `backend/app/agent/html_generator.py` | 新增 `generate_scene_html()`，生成单 scene 自包含 HTML |
| `backend/app/tasks/render_task.py` | 编排 scene 拆分、HF 预渲染、总装 composition 构建、进度事件 |
| `backend/app/rendering/providers/remotion.py` | `can_handle` 接受 `engine in (None, "remotion", "hybrid")`；识别 scene video clip，走总装渲染流程 |
| `backend/app/rendering/engine_selector.py` | 默认返回 `hybrid`，`video-use` 仍为原始素材剪辑优先 |
| `services/renderer/main.py` | 复用 `/render/hyperframes` 处理单 scene HTML 渲染 |
| `services/renderer/remotion/src/compositions/GenericComp.tsx` | 支持 scene video clip 作为底层画面，叠加现有动效层 |

## 5. Scene 模型

Scene 直接沿用 `plan.scenes`：每个 scene 有 `start`、`duration`、`text`、`narration`、`visual`、`transition`、`lower_third`、`visual_type`、`shot`。

`render_task` 把 composition 里 `[start, start+duration)` 范围内的 video/image clip 替换成对应的 HF 预渲染片段；text/overlay 轨保留，让 Remotion 继续叠加字幕和角标。

### 5.1 音频约定

HF 预渲染的 scene 片段**默认无声**（只出画面动画），避免每个 scene 各自混音导致相位/音量不一致。最终音轨仍由现有 `audio_track.py` 生成 `soundtrack.wav`，Remotion 完成混音。

### 5.2 用户体验细节

- **进度颗粒度**：`RenderJob.logs` 记录 `正在生成场景动效 2/5`、`正在合成总时间线` 等场景级事件，前端实时展示进度。
- **单 scene 失败不整片失败**：某 scene LLM HTML 生成失败或 HF 渲染超时，该 scene 自动回退为 Remotion 内置动效（`KenBurns`/`MotionText`/`AmbientCanvas`），`RenderJob.logs` 标记 `scene_{i} 回退 Remotion 默认动效`。
- **scene 片段可复用**：HF 片段按 `project_id + scene_index + sha1(scene_json + composition.style + asset_ids)` 缓存，用户改文案只改了一个 scene 时，其它 scene 直接复用旧片段。
- **scene 预览资产**：HF 输出的 `scene_{i}.mp4` 作为 `source='generated'` 的 `MediaAsset` 落库，素材库展示「第 2 镜动效预览」，支持单独预览。
- **转场仍由 Remotion 统一处理**：HF 片段是“满时长”画面，不带入场/出场动画；scene 之间的 `transition` 由 Remotion 实现，保证整片转场节奏一致。

## 6. 单 Scene HTML 生成

### 6.1 接口

`backend/app/agent/html_generator.py` 新增：

```python
def generate_scene_html(
    scene: dict,
    composition: dict,
    assets: dict[str, str],
) -> str:
    ...
```

- 输入：`scene`（含 start/duration/text/narration/visual/transition/lower_third/visual_type/shot）、`composition`（width/height/fps、metadata.style/mood）、`assets`（scene 可用素材 id → 本地路径）。
- 输出：自包含 HTML 字符串，可直接写入 `<project_dir>/scene_{i}.html` 供 HyperFrames CLI 渲染。

### 6.2 LLM 提示词策略

新增 `GENERATE_SCENE_HTML` 提示词，要求 LLM：

- 输出**自包含 HTML**（无外部依赖，仅使用传入的本地素材路径）。
- 尺寸严格匹配 composition 的 width/height。
- 动画时长等于 `scene.duration`，从 `t=0` 开始。
- 按 `scene.visual` / `composition.metadata.style` 决定视觉风格（粒子、霓虹、胶片、极简等）。
- 必须包含：背景层、素材层（如有 image_index）、文字层（headline/subtext）。**不渲染 lower_third**——角标统一由 Remotion 的 overlay 轨处理，避免与预渲染画面重复。
- 使用 CSS `@keyframes` 做入场、强调、微动效；不处理与下一个 scene 的切换。
- 输出仅 HTML，不要 markdown 代码围栏。

### 6.3 降级链

LLM 失败/超时/输出非法时，走确定性模板 `_fallback_scene_html`：

- 根据 `scene.visual_type` 选模板（product → 大图+左下角标；broll → 图片轮播+光斑；text → 大字排版+粒子背景）。
- 使用现有 `_storyboard_from_composition` / `_render_storyboard` 的简化版，只渲染当前 scene。
- 保底输出可渲染的 HTML，不让 HF 崩溃。

## 7. 渲染流水线编排

### 7.1 新流程

`backend/app/tasks/render_task.py` 在现有流程中，把「HTML → 渲染」改成「Scene HTML → HF 预渲染 → Remotion 总装」。

1. `_write_project_html` 改为 `_write_scene_htmls`：
   - 从 `composition.metadata.plan.scenes` 取 scene 列表。
   - 对每个 scene 调用 `generate_scene_html`，写入 `data/assets/projects/<project_id>/render_<job_id>/scene_{i}.html`。
   - LLM 失败时写入 `_fallback_scene_html` 的结果。

2. 新增 `_prerender_scenes`：
   - 串行/并发调用渲染服务 `POST /render/hyperframes`，把 `scene_{i}.html` 渲染成 `scene_{i}.mp4`。
   - 每个 scene 输出记录到 `RenderJob.logs`，包含耗时与是否回退。
   - 失败 scene 标记为 `fallback_remotion`，不写入 video clip。

3. 新增 `_build_assembly_composition`：
   - 复制原 composition。
   - 对每个 scene 时间范围 `[start, start+duration)`：
     - 移除该范围内所有 `video`/`image` 轨 clip。
     - 插入一个 `video` 轨 clip：`start_time=start`，`duration=duration`，`asset_id=scene_{i}_mp4_asset_id`，`style` 保留原 scene 的 transition/lower_third。
   - text/overlay/audio 轨原样保留。

4. `RenderRequest` 传入 Remotion：
   - `engine` 设为 `hybrid`；`RemotionProvider.can_handle` 会识别该值并按 Remotion 总装流程处理。
   - `assets` 里加入 `scene_{i}.mp4` 的映射。

5. Remotion 渲染 → `/render/mux-audio` → `/render/qa` 不变。

### 7.2 并发与超时

- HF 预渲染默认串行（renderer 是单容器，Chromium 内存压力大），支持 `HF_CONCURRENCY` 环境变量改成 2 并发。
- 单 scene HF 超时 120s；整片 HF 阶段总超时 = scene 数 × 120s + 余量。
- 失败 scene 自动进入 Remotion 回退，不阻塞后续 scene。

### 7.3 进度事件

`RenderJob.logs` 新增事件类型：

- `scene_html_generated {index, total}`
- `scene_prerendered {index, total, path, fallback}`
- `assembly_composition_built {scene_count, fallback_count}`

前端据此展示「第 X/Y 个场景动效已完成」。

## 8. 引擎选择、降级与质量控制

### 8.1 引擎选择

`backend/app/rendering/engine_selector.py` 调整优先级：

1. 有原始视频素材且需要剪辑 → `video-use`
2. 其余情况默认 → `hybrid`
3. `hybrid` 内部失败时按 scene 粒度回退 Remotion 默认动效，不整片切引擎

### 8.2 为什么不再保留“纯 HyperFrames 整片”作为主路径

纯 HyperFrames 的短板是音轨、精确转场、素材代理处理都弱；纯 Remotion 的短板是复杂 HTML/CSS 动效不如手写 CSS 自由。hybrid 把两者的长处拼起来：HF 负责“单镜视觉表现力”，Remotion 负责“整片专业度”。

### 8.3 质量保障设计

- **视觉一致性**：LLM 生成 scene HTML 时，必须传入 `composition.metadata.style/mood` 和全局 `brand_color`；提示词要求所有 scene 保持同一套配色与字体气质。
- **动效曲线**：HTML 统一使用 `cubic-bezier(0.22, 1, 0.36, 1)` 这类缓出曲线；入场时长默认 0.6-0.8s，强调动画 0.3s。
- **文字可读性**：提示词强制 headline 字号 ≥ width/height 的 6%，subtext ≥ 3%，对比度 ≥ 4.5:1；HF 片段输出前用 QA 检测是否黑屏/过曝。
- **转场节奏**：Remotion 根据 `scene.transition` 和 `composition.metadata.rhythm` 决定转场时长（快切 0.3s，舒缓 0.8s）。
- **音画同步**：旁白 TTS 时间戳与 scene 边界对齐；Remotion 混音时以 scene 为单位做音量闪避。

## 9. 测试策略

### 9.1 后端测试

- `backend/tests/rendering/test_hybrid_provider.py`：
  - scene 拆分正确（按 plan.scenes 边界）
  - HF 预渲染调用参数正确
  - 单 scene 失败时自动回退 Remotion，不整片失败
  - assembly composition 的 video clip 替换逻辑正确
- `backend/tests/test_render_task.py`：
  - 新增 hybrid 流程的进度事件断言
  - 缓存复用测试（第二次渲染相同 scene 时不重复调用 HF）

### 9.2 渲染服务测试

- `services/renderer/tests/test_hyperframes.py`：
  - 新增单 scene HTML 渲染成功路径
  - 超时与进程收割
- `services/renderer/tests/test_remotion.py`：
  - 验证 GenericComp 能正确加载 scene video clip 并叠加 text/overlay

### 9.3 端到端

- 新增 `scripts/e2e_hybrid.sh`：
  - 创建项目 → 触发 hybrid 渲染 → 校验最终 MP4 存在、时长正确、非黑屏
  - 校验 `data/assets/.../scene_*.mp4` 数量与 plan.scenes 一致

### 9.4 质量回归

- 每个 PR 跑一个“黄金样例”：固定 prompt + 固定 seed，对比成片关键帧与基线图片的相似度（ffmpeg 抽帧 + 图像哈希），防止动效越改越丑。

## 10. 风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| LLM 生成 HTML 不稳定 | 部分 scene 回退 Remotion | 确定性 `_fallback_scene_html`；scene 级失败不阻断 |
| HF 渲染耗时随 scene 数线性增长 | 用户等待变长 | 场景级进度反馈；scene 片段缓存复用；支持并发开关 |
| 多 scene 风格不一致 | 成片跳跃 | 提示词强制传入全局 style/mood/brand_color；黄金样例回归 |
| 磁盘空间占用增加 | 每个 render job 多 N 个 scene mp4 | 定期清理脚本 `scripts/cleanup_disk.sh`；render job 完成后可清理中间 HTML |
| Remotion 加载本地 scene mp4 失败 | 总装失败 | 确保 scene mp4 路径在 `ASSETS_DIR` 下；Remotion provider 做路径校验 |

## 11. 后续可扩展点

- scene 级重试 API：用户单独重渲某个 scene。
- HF 片段编辑器：在编辑器里微调单 scene 的 HTML 后重新渲染该 scene。
- 模板市场：把优质 scene HTML 模板化，供 LLM 参考或用户直接选用。
