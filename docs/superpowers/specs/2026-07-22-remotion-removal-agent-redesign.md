# ClipWorks 架构精简与 Agent 式 UI 改造设计

> 状态：设计稿待审阅  
> 关联文档：
> - `2026-07-16-hybrid-hyperframes-remotion-design.md`（将被本文档取代其渲染部分）
> - `2026-07-05-clipworks-agentic-ui-design.md`（UI 理念延续，本文档细化落地）

## 1. 背景与问题

当前 ClipWorks 使用 **hybrid 渲染链**：

1. 把 composition 拆成多个 scenes；
2. 每个 scene 单独生成 HTML；
3. HyperFrames 逐个 scene 渲染成 MP4；
4. Remotion 把所有 scene MP4 总装成最终视频。

这条链在 8GB / 4 核的服务器上跑得很吃力：同时存在 **多个 Chromium 进程**（HF scene 渲染 + Remotion 总装），内存很容易爆，且 Remotion 总装本身就需要 2–4GB 内存。

经过代码审查发现，`backend/app/agent/html_generator.py` 里的 `_render_storyboard()` 已经能够生成**包含所有 scene 和完整 CSS 转场**的单个 HTML。HyperFrames 完全有能力一次性渲染整片，不需要 Remotion 来做总装。

因此，本次设计的核心是：

- **移除 Remotion** 作为默认总装引擎；
- **默认使用 HyperFrames 整片渲染**；
- **把 UI 从「工具面板」转向「Agent 对话 + 可视化确认」**；
- **HF 超时/重试交给 LLM/Agent 层决定**。

## 2. 设计目标

| 目标 | 说明 |
|---|---|
| 降低服务器资源消耗 | 8GB 内存服务器能稳定服务更多用户，不再同时跑多个 Chromium |
| 简化渲染架构 | 从「HF 分镜 + Remotion 总装」改为「HF 一次出片 + ffmpeg 混音」 |
| 提升产品体验 | 首页像 Claude/Codex 一样是 Agent 入口，视频专业控制作为二级模式 |
| 消灭抽盲盒感 | 每个关键节点（需求理解、脚本、故事板、导出）都有确认入口 |
| 实时透明 | Agent 思考过程和渲染进度通过 SSE 实时展示给用户 |
| 保留扩展性 | 未来如需复杂时间线总装，仍可用 ffmpeg 或保留 Remotion 作为可选插件 |

## 3. 架构变更：移除 Remotion

### 3.1 当前渲染链（要改的）

```
composition + assets
    ↓
_generate_scene_htmls() → N 个独立 HTML
    ↓
_prerender_scenes() → HyperFrames N 次渲染 → N 个 scene MP4
    ↓
_build_assembly_composition() → 含 scene MP4 的新 composition
    ↓
RemotionProvider → Remotion 总装 → output.mp4
    ↓
ffmpeg mux 音轨
```

### 3.2 新渲染链（目标）

```
composition + assets
    ↓
generate_html() → 单个完整 HTML（所有 scene + CSS 转场）
    ↓
HyperFramesProvider → HyperFrames 一次渲染 → output.mp4
    ↓
ffmpeg mux 音轨（如需要）
```

### 3.3 具体改动点

1. **`backend/app/rendering/providers/remotion.py`**
   - 移除或标记为 deprecated；
   - 如果保留，仅作为可选兜底（不注册到默认 PROVIDERS 列表）。

2. **`backend/app/rendering/service.py`**
   - 从 PROVIDERS 列表移除 `RemotionProvider`；
   - 默认降级链改为：`hyperframes` → `video-use` → `mock`。

3. **`backend/app/rendering/engine_selector.py`**
   - 移除 `hybrid` 默认；
   - 默认返回 `hyperframes`；
   - 有本地视频素材时返回 `video-use`。

4. **`backend/app/tasks/render_task.py`**
   - 移除 `_write_scene_htmls`、`_prerender_scenes`、`_build_assembly_composition` 等 hybrid 专用逻辑；
   - 直接调用 `generate_html()` 生成整片 HTML；
   - 用 `HyperFramesProvider` 渲染；
   - 音轨仍走 `render_soundtrack` + `mux-audio`。

5. **`services/renderer/`**
   - 保留 `/render/hyperframes`、`/render/video-use`、`/render/soundtrack`、`/render/mux-audio`；
   - 移除 `/render/remotion` 端点；
   - Dockerfile 中移除 Remotion 相关 Node 依赖和 Chromium（如果 renderer 不再跑 Remotion，Chromium 仍被 HF 需要）。

6. **`docker-compose.yml`**
   - 如 renderer 不再跑 Remotion，可简化环境变量；
   - worker concurrency 保持或改为 1（根据实测调整）。

### 3.4 风险与兜底

| 风险 | 应对 |
|---|---|
| 整片 HF 渲染超时 | 延长超时时间；HF 失败时 fallback 到 `video-use` 或 mock |
| LLM 生成 storyboard 失败 | 走 `_storyboard_from_composition()` 确定性构造 |
| 模板渲染失败 | 走 `_fallback_html()` 最朴素兜底 |
| 未来需要复杂总装 | Remotion 代码保留在 Git 历史，必要时恢复；或改用 ffmpeg 总装 |

## 4. UI/UX 重新设计：Agent 式视频创作

### 4.1 设计原则

1. **Agent 优先**：首页就是对话入口，用户像对 Claude 说话一样描述需求。
2. **可视化确认**：AI 规划后给出故事板/预览，用户能改文案、换图、调顺序。
3. **进度透明**：渲染步骤实时显示，让用户知道系统在做什么。
4. **专业编辑作为二级模式**：时间线编辑器不默认展示，需要时展开。
5. **Streaming 必须可见**：Agent 思考、规划、调整过程以流式文字呈现，禁止空白 loading。
6. **关键节点必须确认**：需求理解、脚本方案、故事板、导出设置每个节点给用户「确认/修改」入口，减少抽盲盒感。

### 4.2 核心流程

```
[说需求] → [AI 规划] → [可视化确认] → [导出成片]
```

- **说需求**：自然语言、URL、素材上传、风格选择。
- **AI 规划**：生成脚本、分镜、素材列表、时长、画幅。
- **可视化确认**：故事板缩略图 + 手机预览 + Agent 对话修改。
- **导出成片**：选择分辨率/质量/导出位置，显示渲染进度。

### 4.3 页面结构

#### 首页

- 顶部：Logo + 导航（Projects / Billing / Settings）。
- 主区域：大标题 + Agent 输入框。
- 输入框内：文本输入 + 素材/URL/风格快捷按钮 + 生成按钮。
- 底部：快捷提示 + 最近项目卡片。

#### 项目工作区

三栏布局：

- **左侧（Agent 对话）**：历史对话、当前修改、输入框。
- **中间（预览 + 故事板）**：
  - 上半：手机画幅的视频预览；
  - 下半：5 镜故事板缩略图，点击可跳转/编辑。
- **右侧（时间线）**：可折叠，显示 text/visual/audio track，底部有「打开高级编辑器」入口。

#### 导出页

- 分辨率：9:16 / 16:9 / 1:1
- 时长滑块
- 质量：草稿 720p / 成片 1080p / 4K Pro
- 导出位置：云端渲染 / 本机导出（未来客户端模式）
- 实时进度：脚本 → 素材 → 渲染 → 音画合成

### 4.4 关键交互

- 用户在对话中说「把第 3 镜改成...」，Agent 直接修改 composition 并刷新预览。
- 点击故事板缩略图，预览跳转到对应时间点。
- 高级用户可展开时间线做精确剪辑。

## 5. Streaming 与分步确认机制

### 5.1 现状

后端已经实现了多个 SSE endpoint：

- `POST /projects/{id}/agent/chat/stream`：planning 对话流式输出；
- `POST /projects/{id}/agent/vibe/stream`：vibe 创作流式输出；
- `POST /projects/{id}/agent/step/{step_name}`：分步骤执行流式输出；
- `GET /projects/{id}/renders/stream`：渲染任务进度流式输出。

前端 `AgentChat.tsx` 也已支持 token 流式显示，并能从 JSON 中提取 `question` / `plan preview` 展示思考过程；`GenerationPanel.tsx` 已支持 SSE 拉取 render job 的 `logs`、`progress`、`status`。

因此 streaming 基础设施已经存在，本次改造重点是**把现有的 streaming 能力整合进新的 Agent-first 布局，并补齐关键确认点**。

### 5.2 关键确认点

| 确认点 | 触发时机 | 用户可操作 |
|---|---|---|
| **需求理解确认** | Agent 收到用户首轮描述后 | 看到 Agent 总结的「意图卡片」，可一键纠正 |
| **脚本/方案确认** | Agent 生成 plan 后 | 查看标题、钩子、每镜文案/时长，可改、可拒绝、可继续对话 |
| **故事板确认** | composition 构建完成后 | 可视化缩略图 + 手机预览，点击单镜可修改 |
| **导出设置确认** | 点击导出前 | 分辨率、时长、质量、导出位置，最终确认 |

### 5.3 Streaming 展示规范

1. **Thinking 实时可见**
   - Agent 调用 LLM 时，流式 token 直接显示在对话气泡中；
   - 当检测到 JSON/方案结构时，转换为更友好的提示：「AI 正在规划方案：标题…钩子…N 个场景…」。

2. **执行进度实时可见**
   - 渲染阶段显示 Pipeline 步骤（脚本 → 素材 → HTML → HyperFrames → 音画合成）；
   - 每个步骤有 icon + 状态 + 预计耗时；
   - 日志终端滚动显示，最后一条高亮。

3. **失败即时反馈**
   - 任意步骤失败，立刻在对话/进度面板显示原因；
   - 提供「重试」/「降低质量」/「换引擎」/「联系支持」选项。

### 5.4 减少抽盲盒的具体设计

- **不一次性黑盒出片**：用户必须先看到方案并确认，才能进入渲染；
- **渲染前可预览 HTML**：`html_output_url` 在渲染阶段即可在 iframe/弹窗中展示；
- **渲染失败不假装成功**：占位视频（sample.mp4）明确标注，不显示为「已完成」；
- **每个 scene 可单独修改**：点击故事板缩略图，弹出 scene 编辑浮层，改文案/换图/调时长。

## 6. HyperFrames 超时与重试策略

### 6.1 超时设置

- `services/renderer/main.py` 中 `/render/hyperframes` 的 `communicate(timeout=75)` 延长到 **180 秒**。
- `backend/app/rendering/providers/hyperframes.py` 的 httpx 超时同步延长到 **200 秒**。
- `backend/app/tasks/render_task.py` 中 Celery 任务 `time_limit=900` 保持不变，但给 HF 调用留出足够余量。

### 6.2 重试策略

重试不由渲染层硬编码，而是交给 Agent/LLM 决定：

1. **渲染层只报告失败**，不自动重试；
2. `render_task.py` 捕获 HF 失败后，把错误信息写入 `RenderJob.logs`；
3. Agent 层看到失败后，可以：
   - 建议用户缩短视频；
   - 自动降低质量/时长后重试；
   - 切换到 `video-use` 引擎；
   - 返回 mock 预览。

这种设计与用户提到的「像 Codex/Claude Code 调用 HF」一致：工具只负责执行，重试/降级策略由 Agent 推理决定。

### 6.3 进程收割

保留 `_reap_process_group()`，HF 超时或失败时确保 Chromium 孙进程被清理，避免 8GB 机器上僵尸进程累积。

## 6. 文档更新清单

Remotion 移除后，以下文档需要更新：

| 文档 | 更新内容 |
|---|---|
| `README.md` | 移除 Remotion 引擎描述；更新为 HF 整片渲染 |
| `AGENTS.md` | 更新渲染架构、本地端口、故障排查 |
| `docs/design/clipworks-design.md` | 更新设计系统相关描述（如有渲染相关部分） |
| `2026-07-16-hybrid-hyperframes-remotion-design.md` | 标记为已废弃，指向本文档 |
| `docker-compose.yml` 注释 | 更新内存/并发建议 |
| 代码注释 | `render_task.py`、`service.py`、`engine_selector.py` 中涉及 Remotion 的注释 |

## 7. 验收标准

1. `docker compose up` 后，renderer 容器不依赖 Remotion 也能正常工作；
2. 默认创建项目并渲染，走 `hyperframes` 引擎，不再调用 `/render/remotion`；
3. 8GB 内存服务器上，worker concurrency=1 时能稳定渲染 1 分钟视频；
4. 现有测试通过或更新：`tests/rendering/test_remotion_provider.py`、`tests/test_render_task.py`、`tests/test_render_integration.py`；
5. 首页 UI 改造完成，呈现 Agent 式对话入口 + 最近项目列表；
6. 项目工作区呈现三栏布局（对话 / 预览+故事板 / 时间线）；
7. 导出页呈现分辨率/时长/质量/进度；
8. Agent planning 对话有流式 thinking 展示，不显示空白 loading；
9. 脚本方案、故事板、导出设置都有用户确认步骤；
10. 渲染失败时明确提示原因，不将占位视频显示为「已完成」。

## 8. 实施顺序建议

### Phase 1：后端架构精简（高优先级）

1. 修改 `engine_selector.py` 默认引擎为 `hyperframes`；
2. 修改 `service.py` 移除 RemotionProvider 默认注册；
3. 简化 `render_task.py`：直接 `generate_html()` + HyperFrames 渲染；
4. 延长 HF 超时；
5. 更新/移除相关测试；
6. 验证 8GB 服务器稳定渲染。

### Phase 2：文档清理

1. 更新 `README.md`、`AGENTS.md`；
2. 废弃旧 hybrid 设计文档；
3. 更新代码注释。

### Phase 3：前端 UI 改造

1. 首页改为 Agent 对话入口；
2. 新建项目工作区三栏布局；
3. 整合现有 SSE：把 `AgentChat` 和 `GenerationPanel` 的流式能力接入新布局；
4. 补齐关键确认点：需求理解卡片、脚本方案确认、故事板确认、导出设置确认；
5. 渲染进度面板实时显示 Pipeline 步骤和日志；
6. 新建导出页；
7. 适配移动端。

## 9. 未决问题

以下问题需要在实现前或实现中确认：

1. Remotion 代码是**完全删除**还是**保留为可选插件**？（建议保留 Git 历史，代码先移除）
2. renderer 容器是否还需要 Chromium？（HyperFrames 仍需要，所以 still 需要）
3. 前端 UI 改造是**重写 Next.js 前端**还是在现有基础上调整？（建议调整，而非重写）
4. 本机导出（客户端渲染）是否在本次范围内？（建议本次只做 UI 占位，实现放到后续）

---

*设计完成时间：2026-07-22*  
*Visual Companion 会话：`.superpowers/brainstorm/60064-1784716240/`*
