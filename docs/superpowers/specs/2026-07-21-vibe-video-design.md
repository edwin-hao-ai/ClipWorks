# Vibe Video 设计文档

> 将 ClipWorks 项目工作区从「四步表单向导」改造成「LLM 驱动的对话式视频创作 Agent」，类似 vibe coding：用户用自然语言描述，Agent 自主推进脚本、素材、场景、动效、渲染，右侧实时画布同步呈现每一步结果。

## 1. 背景与目标

### 1.1 现状问题

当前项目工作区在 `draft/planning` 状态时使用 `PlanWizard`：

- 4 个步骤标签：脚本 → 素材 → 场景 → 动效
- 每步都是表单/卡片式 UI
- 用户必须手动点击「下一步」

这与产品定位的「一句话，一段素材，一条成片」以及用户确认的「一定要是 agent 模式，包括用户体验和界面」不一致。

### 1.2 目标

实现 **Vibe Video** 体验：

1. 用户用自然语言与 AI 导演对话。
2. AI 自动按内部 workflow 推进：理解需求 → 脚本 → 素材 → 场景 → 动效 → 渲染。
3. 右侧实时画布随进度更新，用户可随时查看和编辑。
4. 关键步骤 AI 主动询问确认，避免「抽卡」式开盲盒。
5. 保留用户随时打断、修改、重来的能力。

## 2. 设计原则

参考当前 vibe coding Agent（Claude Code、Cursor Agent、Replit Agent）的共性：

- **Chat-first**：主界面是对话，不是表单。
- **LLM orchestration**：LLM 决定调用什么工具、何时推进、何时询问。
- **Tool loop**：LLM → 决策 → 执行工具 → 结果回传 → 循环。
- **实时画布**：右侧可视化反馈，类似 Replit 的「聊天 + 实时预览」。
- **Human-in-the-loop**：关键动作前确认，但支持 autonomy slider（以后不再问）。
- **Error withholding**：可恢复错误先内部重试/补偿，不行了再告诉用户。

## 3. 整体 UX 流程

打开项目工作区后，界面统一为左右两栏：

```
┌─────────────────────────────────────────────────────────────┐
│  Sidebar  │  TopBar（项目标题 + 导出/删除）                    │
│           ├─────────────────────────────────────────────────┤
│           │  左侧 Agent Chat          │  右侧实时画布          │
│           │  （占 5/12）              │  （占 7/12）           │
│           │                           │                       │
│           │  1. workflow 状态条        │  1. 根据 step 切换：   │
│           │  2. 聊天记录               │     - 需求摘要卡       │
│           │  3. 输入框 + 快捷提示      │     - 脚本卡           │
│           │                           │     - 素材板           │
│           │                           │     - 场景故事板        │
│           │                           │     - 动效说明         │
│           │                           │     - 视频预览         │
│           │                           │  2. 支持直接编辑        │
└───────────┴───────────────────────────┴───────────────────────┘
```

### 3.1 左侧 Agent Chat

- **Workflow 状态条**：仅作可视化进度，不可点击。Agent 推进时高亮当前步骤。
- **聊天记录**：
  - `thinking`：AI 思考中…
  - `question`：AI 的问题气泡
  - `artifact`：方案/素材/场景等摘要卡片，点击可跳右侧画布
  - `progress`：轻量进度条
  - `text`：普通回复
- **输入框**：自然语言输入，支持快捷提示。
- **Autonomy 控制**：用户可设置「每步都确认 / 仅渲染前确认 / 全交给 AI」。

### 3.2 右侧实时画布

根据 `agent_state.step` 自动切换展示内容：

| step | 画布内容 |
|---|---|
| `understand` | 需求摘要卡（用途、时长、画幅、风格、目标受众） |
| `script` | 脚本卡（标题、钩子、叙事弧线、CTA、时长、画幅） |
| `assets` | 素材板（所需素材列表 + 已配图/视频） |
| `scenes` | 场景故事板（时间线 + 每场景描述/文案） |
| `effects` | 动效说明（每场景视觉风格、动画关键词） |
| `render` | 生成进度 + 最终视频预览 |
| `done` | 成片预览 + 下载按钮 |

画布中的字段支持直接编辑，编辑后自动作为一条修改请求发给 Agent。

### 3.3 典型用户旅程

1. 用户首页输入：「帮我做一个 30 秒的小红书产品视频，风格活泼」。
2. 进入工作区，Agent 说：「Hi，我来帮你。我先确认一下：你是想推广哪款产品？」。
3. 用户回答。
4. Agent 内部跑 `understand`，生成需求摘要，展示在右侧。
5. Agent 问：「时长 30 秒、画幅 9:16、风格活泼，对吗？」
6. 用户说「对」。
7. Agent 内部跑 `generate_script`，右侧显示脚本卡，聊天里问：「脚本方向 OK 吗？」
8. 用户说「钩子再犀利一点」。
9. Agent 在当前 step 修改，再次等待确认。
10. 用户说「下一步」。
11. Agent 依次跑 `collect_assets`、`build_scenes`、`design_effects`，每步都展示并询问。
12. 用户说「生成视频」。
13. Agent 调用 `render_video`，右侧显示进度，完成后展示成片。

## 4. 后端 Agent Loop 架构

### 4.1 核心循环

后端维护一个 `AgentSession`，核心是一个 `while` 循环：

```python
while session.step != 'done':
    1. 把当前状态 + 用户消息 + 可用工具 发给 LLM（Architect）
    2. LLM 输出决策：ask / run_tool / advance / render
    3. 如果是 run_tool，调用对应 step 生成器（Editor 模型或确定性函数）
    4. 工具执行结果写回状态
    5. 判断是否需要用户确认
       - 需要：yield 聊天消息，等待用户下一条
       - 不需要：继续循环
```

### 4.2 可用工具

| 工具 | 作用 | 输入 | 输出 |
|---|---|---|---|
| `understand` | 提炼用户需求 | 用户对话历史 | 需求摘要 JSON |
| `generate_script` | 生成脚本 | 需求摘要 | 脚本 JSON |
| `collect_assets` | 搜索/生成素材 | 脚本 | 素材列表 + 配图 |
| `build_scenes` | 生成场景时间线 | 脚本 + 素材 | 场景列表 JSON |
| `design_effects` | 设计每场景动效 | 场景 | 动效列表 JSON |
| `render_video` | 调用渲染任务 | 完整方案 | render job id |
| `ask_user` | 向用户提问 | 问题文本 | 无 |

### 4.3 LLM 决策输出格式

每次调用 Architect 模型，要求输出结构化 JSON：

```json
{
  "thinking": "用户在确认脚本，我觉得脚本 OK，可以推进到素材。",
  "action": "advance",
  "target_step": "assets",
  "response_to_user": "脚本方向 OK，我去准备素材。",
  "payload": {
    "script": { "title": "...", "hook": "..." }
  },
  "requires_confirmation": true,
  "confirmation_message": "脚本方向 OK 吗？"
}
```

`action` 枚举：

- `ask`：向用户提问，不推进。
- `run_tool`：执行某个工具（如 `generate_script`）。
- `advance`：推进到下一个 step。
- `revise`：在当前 step 内修改。
- `reset`：清空状态回 `understand`。
- `render`：调用渲染。

### 4.4 确认策略

每完成一个工具后，Architect 判断是否需要用户确认：

- 结果是否完整？
- 是否有歧义？
- 是否高成本动作（如渲染）？
- 当前 `autonomy_level` 是什么？

默认 `confirm_each`，用户可以提升到 `confirm_render_only` 或 `full_auto`。

### 4.5 错误恢复

参考 Claude Code 的 error withholding：

1. **LLM 输出无法解析**：用 fallback 策略重跑一次当前 step。
2. **工具执行失败**：Agent 自己决定重试、换方案或问用户。
3. **额度不足（402）**：立即停止，前端展示升级提示。
4. **网络/超时**：内部重试 1 次，仍失败再告诉用户。

所有错误都以 Agent 聊天消息形式呈现。

## 5. 前后端协议

### 5.1 前端请求

```http
POST /agent/chat/stream
Content-Type: application/json

{ "message": "用户说的自然语言" }
```

### 5.2 后端流式事件

统一事件格式：

```json
{ "type": "thinking", "text": "AI 在规划…" }
{ "type": "question", "text": "你希望时长是多少？" }
{ "type": "artifact", "kind": "script", "data": {...} }
{ "type": "progress", "step": "assets", "status": "running" }
{ "type": "error", "message": "…", "recoverable": true }
{ "type": "done" }
```

### 5.3 agent_state 扩展

```json
{
  "step": "script",
  "messages": [...],
  "autonomy_level": "confirm_each",
  "pending_plan": {...},
  "payload": {
    "understand": {...},
    "script": {...},
    "assets": {...},
    "scenes": {...},
    "effects": {...}
  },
  "last_action": "advance",
  "last_user_message": "..."
}
```

## 6. 前端组件调整

### 6.1 保留并复用

- `AgentChat.tsx`：扩展为支持 planning 模式，作为左侧主聊天面板。
- `ScriptPanel`、`AssetsPanel`、`ScenesPanel`、`EffectsPanel`：从向导步骤改为右侧画布的 artifact 渲染组件。
- `GenerationPanel`：渲染进度和成片预览。

### 6.2 移除/隐藏

- `PlanWizard.tsx` 及其 4 步 tab 导航不再作为主界面。
- 项目页面不再因 `draft/planning/generating/ready` 切换完全不同的布局。

### 6.3 新增

- `AgentCanvas.tsx`：右侧实时画布，根据 step 切换显示不同 artifact。
- `WorkflowStatusBar.tsx`：顶部 workflow 进度条。
- `AutonomySelector.tsx`：确认级别选择器。

## 7. 后端模块调整

### 7.1 新增

- `app/agent/session.py`：`AgentSession` 状态机。
- `app/agent/orchestrator.py`：Architect LLM 调用 + action 路由。
- `app/agent/tools.py`：工具实现（复用现有 steps 逻辑）。
- `app/routers/agent_chat.py`：`POST /agent/chat/stream` 端点。

### 7.2 保留但不再直接暴露给前端

- `app/routers/agent.py` 中的 `/agent/step/{name}` 作为内部工具保留。
- `app/agent/steps.py` 中的 step 生成器被 tools.py 包装调用。

### 7.3 数据模型

`Project.agent_state` 已经支持 JSON，直接扩展字段即可，不需要新表。

## 8. 测试策略

### 8.1 后端

- 测试 `AgentSession` 状态机：mock LLM 输出，验证 action 选择和 step 推进。
- 测试每个 tool 的执行和 fallback。
- 测试确认策略在不同 `autonomy_level` 下的行为。
- 测试错误恢复路径。

### 8.2 前端

- 测试 `AgentChat` 渲染不同类型的消息。
- 测试 `AgentCanvas` 根据 step 切换 artifact。
- 测试画布编辑后自动发送修改请求。

### 8.3 e2e

- 更新 `scripts/e2e_agent_loop.py`，用自然语言跑完整 vibe video 流程。
- 验证从需求输入到 `render_video_task` 入队的完整链路。

## 9. 里程碑

### Milestone 1：基础 Chat + Canvas

- 后端新增 `/agent/chat/stream`。
- 前端工作区改成左右布局。
- `understand` 和 `script` 两步可用。

### Milestone 2：完整 Workflow

- 补齐 `assets`、`scenes`、`effects`、`render`。
- 右侧画布支持所有 artifact。

### Milestone 3：体验打磨

- autonomy slider。
- 错误恢复优化。
- e2e 脚本覆盖。

## 10. 参考

- [A Survey of Vibe Coding with Large Language Models](https://arxiv.org/html/2510.12399v2)
- [Why Claude Code's Agent Loop Is Over 1,400 Lines](https://internals.laxmena.com/p/why-claude-codes-agent-loop-is-over)
- [Claude Code Agent Loop: Dissecting the Heart of an AI Coding Assistant](https://blog.vincentqiao.com/en/posts/claude-code-agent-loop/)
- [Exploring Student-AI Interactions in Vibe Coding](https://arxiv.org/html/2507.22614v1)（Replit 的 chat + live preview 模式）
