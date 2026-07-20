# ClipWorks Agent Loop 向导设计

> 日期：2026-07-16
> 状态：已确认，待实施
> 目标：把 Agent 视频创作流程从「一问一答直接出 plan」改造为「脚本 → 素材 → 场景 → 动效」四步递进式 Agent loop，并配套向导式 UI。

## 1. 背景与问题

当前 ClipWorks 的 Agent 规划流程是单步的：

1. 用户在 AgentChat 输入 brief。
2. Planning Agent 要么问一个澄清问题，要么直接输出完整 plan（含 scenes、assets_needed、engine_hint）。
3. 用户确认后，后端一次性 `build_composition(plan)` 并渲染。

这种模式对于简单视频够用，但存在几个问题：

- **中间结果不可见**：用户看不到 Agent 是怎么从 brief 推到 scenes 的，也很难在生成前干预脚本、素材、动效。
- **难以做复杂视频**：当用户想要特定角色、特定视觉风格、特定素材来源时，单步 prompt 很容易遗漏。
- **缺乏专业感**：参考商汤 U1 Pro 等交付级创作 Agent，真正的视频创作应该是一个多步迭代 loop：理解 → 脚本 → 资源 → 分镜 → 执行 → 修正。

用户希望 ClipWorks 的 Agent 也采用类似的 loop：先想脚本和角色，再确定素材和资源，再设计场景，最后拆解每场景的 HTML 动画效果和是否需要生成图。

## 2. 目标

- 把 Agent 规划拆成四个显式步骤：**Script → Assets → Scenes → Effects**。
- 每步由独立 LLM Agent 驱动，输出结构化数据，用户可在向导中确认或编辑。
- 提供清晰的向导式 UI，显示步骤进度、当前步骤内容、上一步/下一步/重新生成控制。
- 保持向后兼容：现有 `/chat/stream` 接口和自由对话模式保留。
- 每步都有确定性 fallback，LLM 失败时用户仍可继续。

## 3. 非目标

- 不替换现有的 composition 模型和渲染流水线；四步完成后仍调用 `build_composition` + hybrid 渲染。
- 不在本方案中实现 AI 自动生成图（Midjourney/DALL·E 等集成）；仅标记「是否需要生成图」及给出生成 prompt，为后续扩展留接口。
- 不改造现有的 modify/chat 模式；向导模式与其并存。

## 4. 总体架构

### 4.1 四步流程

```
用户输入 brief
  → Step 1 Script：产出 title / hook / 角色 / 叙事弧线 / CTA
  → Step 2 Assets：列出所需图片/视频/音乐/生成图及其检索词
  → Step 3 Scenes：把脚本拆成 scenes（时间、画面、文案、镜头、转场）
  → Step 4 Effects：为每个 scene 指定 HTML 动画风格、是否需要生成图
  → 用户确认 → build_composition(plan) → hybrid 渲染
```

### 4.2 状态机

```
idle ──► script ──► assets ──► scenes ──► effects ──► approved
            ▲          ▲          ▲          ▲
            └──────────┴──────────┴──────────┘ (back 可回退)
```

`agent_state.step` 表示当前所在步骤；`agent_state.generating_step` 标记当前正在生成的步骤，防止并发冲突。

### 4.3 数据模型扩展

`Project.agent_state` 扩展为：

```json
{
  "step": "script|assets|scenes|effects|approved",
  "generating_step": null,
  "messages": [...],
  "script": {
    "title": "...",
    "hook": "...",
    "roles": [{"name": "...", "perspective": "..."}],
    "narrative_arc": "...",
    "cta": "...",
    "duration": 30,
    "format": "16:9"
  },
  "assets": {
    "needed": [
      {"type": "image|video|music|generated_image", "description": "...", "query": "...", "count": 1}
    ]
  },
  "scenes": [
    {"start": 0, "duration": 5, "description": "...", "visual": "...", "text": "...", "visual_type": "...", "shot": "...", "transition": "...", "lower_third": "...", "required_assets": [0]}
  ],
  "effects": [
    {"scene_index": 0, "visual_style": "...", "animation_keywords": ["..."], "generate_image": false, "generate_image_prompt": "..."}
  ],
  "pending_plan": null
}
```

### 4.4 模块职责

| 模块 | 职责 |
|---|---|
| `backend/app/agent/steps/script_step.py` | 脚本 Agent：产出标题、钩子、角色、叙事弧线、CTA |
| `backend/app/agent/steps/assets_step.py` | 素材 Agent：列出所需素材及检索词/生成 prompt |
| `backend/app/agent/steps/scenes_step.py` | 场景 Agent：把脚本拆成 scenes |
| `backend/app/agent/steps/effects_step.py` | 动效 Agent：为每个 scene 指定 HTML 动画风格和生成图需求 |
| `backend/app/agent/steps/__init__.py` | 统一 `run_step(step_name, project, state, user_input)` 调度 |
| `backend/app/routers/agent.py` | 新增 `/state`、`/step/{step_name}`、`/back`、`/reset`、`/approve` 端点 |
| `frontend/src/components/project/PlanWizard.tsx` | 四步向导主组件 |
| `frontend/src/components/project/ScriptPanel.tsx` | Script 步骤展示/编辑 |
| `frontend/src/components/project/AssetsPanel.tsx` | Assets 步骤展示/编辑 |
| `frontend/src/components/project/ScenesPanel.tsx` | Scenes 步骤展示/编辑 |
| `frontend/src/components/project/EffectsPanel.tsx` | Effects 步骤展示/编辑 |
| `frontend/src/lib/types.ts` | 扩展 `AgentState`、`AgentPlan`、`AgentStep` 类型 |

## 5. 后端 Step 模块

### 5.1 统一接口

每个 step 模块实现：

```python
def run(project: Project, state: dict, user_input: Optional[str] = None) -> Iterator[str]:
    """Yields SSE chunks and mutates state in-place with the step's output."""
    ...
```

调度器：

```python
STEPS = {
    "script": script_step,
    "assets": assets_step,
    "scenes": scenes_step,
    "effects": effects_step,
}

def run_step(step_name: str, project, state, user_input=None):
    return STEPS[step_name].run(project, state, user_input)
```

### 5.2 Script Step

**输入**：用户 brief、source_url、target_format、target_duration、历史消息。

**输出 schema**：

```json
{
  "title": "视频标题",
  "hook": "3 秒内抓住注意力的钩子",
  "roles": [
    {"name": "旁白/视角", "perspective": "第一人称/品牌方/用户"}
  ],
  "narrative_arc": "钩子 → 冲突/痛点 → 揭示/产品登场 → 证据/体验 → CTA",
  "cta": "结尾行动号召",
  "duration": 30,
  "format": "16:9"
}
```

**Prompt 要求**：
- 必须先想角色和叙事弧线，再写 hook 和 CTA。
- 拒绝干巴巴参数罗列，用故事语言表达。
- 如果用户已指定 duration/format，直接使用不再询问。

### 5.3 Assets Step

**输入**：script 输出 + 用户 brief。

**输出 schema**：

```json
{
  "needed": [
    {"type": "image", "description": "产品主图", "query": "modern SaaS dashboard mockup", "count": 1},
    {"type": "generated_image", "description": "科技感背景", "query": "dark blue tech particles abstract background", "count": 1},
    {"type": "music", "description": "轻快科技感 BGM", "query": "upbeat tech ambient background music", "count": 1}
  ]
}
```

**Prompt 要求**：
- 明确区分搜索图、生成图、实拍素材、音乐。
- 生成图要给出可直接喂给文生图模型的英文 prompt。
- 数量控制在合理范围（通常 3-6 项）。

### 5.4 Scenes Step

**输入**：script + assets + 用户 brief。

**输出 schema**：与现有 `plan.scenes` 一致，但增加 `required_assets`：

```json
{
  "scenes": [
    {
      "start": 0,
      "duration": 5,
      "description": "...",
      "visual": "...",
      "text": "...",
      "visual_type": "product|broll|metaphor|text",
      "shot": "特写",
      "transition": "fade",
      "lower_third": "...",
      "required_assets": [0, 1]
    }
  ]
}
```

**Prompt 要求**：
- 严格按 script 叙事弧线拆 scenes。
- 首镜 3 秒内抓人。
- 每镜文案 <=14 字，旁白 <=18 字。
- 优先使用 assets 中列出的素材。

### 5.5 Effects Step

**输入**：scenes + composition context（width/height/style/mood）。

**输出 schema**：

```json
{
  "effects": [
    {
      "scene_index": 0,
      "visual_style": "深蓝科技粒子",
      "animation_keywords": ["粒子", "HUD", "淡入"],
      "generate_image": false,
      "generate_image_prompt": ""
    }
  ]
}
```

**Prompt 要求**：
- 为每个 scene 指定中文视觉风格关键词（用于 `_scene_palette` 和 HTML 生成）。
- 判断是否需要额外生成图；需要则给出 prompt。
- 动画关键词用于 `generate_scene_html` 的 visual 描述。

## 6. API 端点与数据流

### 6.1 新增/调整端点

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/projects/{id}/agent/state` | 获取当前 agent_state |
| POST | `/projects/{id}/agent/step/{step_name}` | 运行某一步 Agent，SSE 返回 |
| POST | `/projects/{id}/agent/back` | 回退到上一步 |
| POST | `/projects/{id}/agent/reset` | 清空 agent_state，重新开始 |
| POST | `/projects/{id}/agent/approve` | 从四步数据构建 plan 并触发渲染 |
| POST | `/projects/{id}/agent/state` | 用户手动编辑后保存 state |

### 6.2 数据流

```
用户输入 brief
  → POST /step/script (SSE)
    → agent_state.step = "script", generating_step = "script"
    → 流式输出 title/hook/roles/narrative_arc/cta
    → 输出完成后 agent_state.script = {...}, step = "script", generating_step = null
  → 用户在向导确认/编辑
  → POST /step/assets (SSE)
    → agent_state.assets = {...}
  → ...scenes, effects
  → POST /approve
    → 把 script + assets + scenes + effects 合并成 plan
    → build_composition(plan)
    → render_video_task.delay(...)
    → agent_state.step = "approved"
```

### 6.3 与现有代码的兼容

- 保留 `/chat/stream` 作为自由对话入口；如果 `agent_state.step` 为空，前端可以引导用户进入向导。
- `/approve` 兼容旧 `pending_plan`：如果 `agent_state.pending_plan` 存在而四步数据不存在，仍按旧逻辑处理。

## 7. 前端向导 UI

### 7.1 组件结构

```
PlanWizard
├── StepSidebar          // 左侧步骤条
│   ├── Script
│   ├── Assets
│   ├── Scenes
│   └── Effects
└── StepContent
    ├── ScriptPanel
    ├── AssetsPanel
    ├── ScenesPanel
    └── EffectsPanel
```

### 7.2 每一步的 UI

**ScriptPanel**
- 标题、钩子输入框
- 角色卡片列表（可增删改）
- 叙事弧线文本区
- CTA 输入框
- 时长/画幅显示（来自项目设置）

**AssetsPanel**
- 素材表格/卡片：类型、描述、检索词、数量
- 每项可删除、编辑
- 「添加素材」按钮

**ScenesPanel**
- 时间轴/卡片形式展示 scenes
- 每卡显示：时间、画面描述、文案、镜头、转场
- 支持拖拽排序、增删、编辑

**EffectsPanel**
- 每个 scene 一张卡片
- 显示/编辑：视觉风格、动画关键词、是否需要生成图、生成图 prompt
- 提供常见风格快捷选择（科技粒子、暖橙光晕、极简高级等）

### 7.3 全局控制

- 每页底部：「上一步」「重新生成」「下一步」按钮。
- 所有步骤完成后：「确认生成」按钮。
- 顶部显示当前 Agent 是否正在生成（`generating_step`）。

### 7.4 与 AgentChat 的关系

- AgentChat 作为侧边辅助保留，用户仍可打字与 Agent 对话。
- Agent 能识别当前 `step` 并做出相应回复（例如当前在 effects 步骤时，用户说「让第一镜更炫」，Agent 只修改 effects[0]）。

## 8. 错误处理与降级

### 8.1 每步 LLM 失败降级

| Step | Fallback |
|---|---|
| script | 复用 `app.agent.conversation.build_fallback_plan(project)` 中的脚本/标题/钩子/CTA 字段 |
| assets | 从 script 关键词推断 3-5 项基础素材需求 |
| scenes | 复用 `build_fallback_plan` 的 scenes 并按项目时长归一化 |
| effects | 为每个 scene 分配默认视觉风格（基于 scene.visual 关键词） |

### 8.2 用户可干预

- 任何一步 Agent 输出不满意，用户可直接编辑，然后点「重新生成」让 Agent 基于修改后的输入再跑。
- 如果 Agent 输出无法解析为合法 JSON，前端显示原始文本并提示用户手动修正。

### 8.3 越步与并发

- 用户未 script 就调用 `/step/scenes`：返回 400，提示先完成前置步骤。
- 当前已有 step 在生成时再次调用：返回 409，提示等待完成。

## 9. 测试策略

### 9.1 后端测试

- `backend/tests/agent/test_steps.py`：
  - 每个 step 的 LLM 输出解析正确。
  - fallback 逻辑覆盖。
  - 状态机转换正确。
- `backend/tests/test_agent_router.py`：
  - `/agent/state` 返回正确。
  - `/step/{step_name}` SSE 输出正常。
  - `/back`、`/reset` 行为正确。
  - `/approve` 能构建 composition 并触发 render。
  - 越步调用返回 400，并发调用返回 409。

### 9.2 前端测试

- `frontend/tests/components/PlanWizard.test.tsx`：
  - 按 step 渲染对应 panel。
  - 点击下一步调用正确 API。
  - 用户编辑后 state 更新。
  - approve 触发回调。

### 9.3 端到端

- `scripts/e2e_agent_loop.py`：API 级别验证四步流程到渲染完成。
- `scripts/e2e_agent_loop_ui.py`：Playwright 验证向导页面交互。

## 10. 风险与缓解

| 风险 | 影响 | 缓解 |
|---|---|---|
| 四步流程拉长用户操作路径 | 简单视频反而更慢 | 提供「一键生成」快捷入口，直接走四步默认方案 |
| LLM 每步单独调用增加成本和延迟 | 费用/等待时间上升 | 每步可缓存、可取消；未来支持一次性生成完整 plan 再分步展示 |
| 状态机复杂导致 bug | 用户卡在中间状态 | 增加 `/reset`、fallback、清晰的错误提示 |
| 前端向导组件变复杂 | 维护成本上升 | 每个 panel 独立组件，通过统一 state 驱动 |

## 11. 后续可扩展点

- AI 自动生成图集成：当 `effects[i].generate_image=true` 时自动调用文生图模型。
- 每步支持「版本对比」：保存历史生成结果，用户可切换对比。
- 语音/音色选择 step：在 assets 后增加旁白音色和 BGM 风格选择。
- Agent 自动修正 loop：渲染完成后根据用户反馈反向修改 script/assets/scenes/effects。
