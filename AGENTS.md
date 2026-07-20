# ClipWorks 映工厂 - Agent 项目指南

> 本文件供 AI 编程 Agent 阅读。它假设读者对项目一无所知，并汇总了项目的架构、技术栈、构建/测试命令、代码组织方式、开发约定和安全注意事项。

## 1. 项目概述

ClipWorks（映工厂）是一个 AI 驱动的视频生成与剪辑工具，口号是“一句话，一段素材，一条成片”。用户输入一句话需求或素材 URL，系统会自动规划视频脚本、生成时间线合成，并渲染输出真实 MP4。

项目当前处于原型/MVP 阶段，后端 Agent 和渲染流水线在 Kimi API 或渲染引擎不可用时均有确定性降级方案。

### 1.1 仓库结构

```
ClipWorks/
├── backend/              # FastAPI 后端 + Agent 逻辑 + 渲染调度
├── frontend/             # Next.js 14 前端（App Router）
├── services/renderer/    # 独立渲染服务（多引擎真实 MP4 输出）
├── docs/                 # 设计文档与 superpowers 计划
├── scripts/              # 端到端测试脚本
├── data/assets/          # 运行时素材/输出目录（gitignored）
├── docker-compose.yml    # 本地开发一键启动
└── AGENTS.md             # 本文件
```

## 2. 技术栈

### 2.1 后端

- **框架**：FastAPI 0.111+，Python 3.11+
- **数据库**：PostgreSQL 16，SQLAlchemy 2.0+，Alembic 迁移
- **缓存/队列**：Redis 7 + Celery 5.4+（异步渲染任务）
- **LLM**：OpenAI SDK 兼容接口，默认调用 Kimi API（`KIMI_API_KEY`）
- **依赖管理**：`pyproject.toml` + `requirements.txt`（Docker 使用 requirements.txt）
- **网页抓取**：`httpx` + `beautifulsoup4`

### 2.2 前端

- **框架**：Next.js 14.2+（App Router），React 18，TypeScript 5
- **样式**：Tailwind CSS 3.4+，CSS 变量设计系统（暗色优先）
- **状态管理**：Zustand（认证状态）
- **测试**：Vitest + jsdom + Testing Library
- **图标**：lucide-react
- **工具类**：clsx

### 2.3 渲染服务

- **框架**：FastAPI + Python 3 / Node.js 22 混合容器
- **引擎 1 - HyperFrames**：基于 Node.js 的 HTML/CSS 动画渲染（`npx hyperframes render`）
- **引擎 2 - Remotion**：基于 React 组件的模板渲染（`@remotion/cli`）
- **引擎 3 - video-use**：原始素材剪辑引擎。spec 驱动（clips 的 trim_start/trim_duration + 画幅 + 可选 BGM），一条 ffmpeg filter_complex 完成 trim/scale/pad/concat + BGM 混入，输出 H.264/AAC MP4；只依赖 ffmpeg，不需要 Chromium
- **容器依赖**：ffmpeg、Chromium、Playwright

### 2.4 基础设施

- **容器化**：Docker + Docker Compose
- **服务**：PostgreSQL、Redis、backend、worker、renderer、frontend
- **本地端口**：
  - 前端：http://localhost:3000
  - 后端 API：http://localhost:8000
  - 渲染服务：http://localhost:8001
  - PostgreSQL：localhost:5432
  - Redis：localhost:6379

## 3. 架构与代码组织

### 3.1 后端模块划分

```
backend/app/
├── main.py               # FastAPI 应用入口、路由挂载、静态文件、健康检查
├── config.py             # 环境变量加载（backend/.env）
├── database.py           # SQLAlchemy engine/session/Base
├── models.py             # 数据库模型（User/Project/Composition/Track/Clip/MediaAsset/Script/RenderJob）
├── schemas.py            # Pydantic 输出模型
├── celery_app.py         # Celery 配置
├── seed.py               # 数据库种子数据
├── routers/              # API 路由
│   ├── auth.py           # mock OAuth（cookie session）
│   ├── projects.py       # 项目 CRUD
│   ├── compositions.py   # 合成时间线读写
│   ├── assets.py         # 素材上传
│   ├── renders.py        # 渲染任务触发
│   └── agent.py          # Agent 对话修改合成
├── agent/                # AI Agent 核心
│   ├── llm.py            # KimiClient 封装
│   ├── prompts.py        # 系统提示词
│   ├── planner.py        # 视频规划（plan_video）
│   ├── composer.py       # 合成构建（build_composition）
│   ├── html_generator.py # 生成 HyperFrames HTML
│   └── modifier.py       # 自然语言修改合成
├── rendering/            # 渲染调度层
│   ├── provider.py       # RenderProvider 协议 + RenderRequest/RenderResult
│   ├── service.py        # RenderService（按引擎优先级降级）
│   ├── engine_selector.py# 默认引擎选择逻辑
│   └── providers/        # 各引擎实现：hyperframes/remotion/video_use/mock
└── services/             # 业务工具
    ├── scraper.py        # 网页元数据抓取
    └── assets.py         # 图片下载/素材持久化
```

### 3.2 前端模块划分

```
frontend/src/
├── app/                  # Next.js App Router 页面
│   ├── page.tsx          # 启动页/项目创建
│   ├── login/page.tsx    # 登录页
│   ├── projects/page.tsx # 项目列表
│   ├── projects/[id]/page.tsx       # 项目工作区
│   ├── projects/[id]/editor/page.tsx # 时间线编辑器
│   ├── projects/[id]/assets/page.tsx # 素材库
│   ├── settings/page.tsx
│   ├── billing/page.tsx
│   ├── privacy/page.tsx    # 隐私政策（草案 v0.1，公开访问，法务审订前不得去掉草案声明）
│   ├── terms/page.tsx      # 服务条款（同上；登录页页脚链接到这两页）
│   ├── layout.tsx
│   └── globals.css       # 设计系统 CSS 变量
├── components/
│   ├── ui/               # 基础 UI（Button 等）
│   ├── layout/           # Sidebar、TopBar、AuthGuard、LegalLayout（法律页面共享骨架）
│   ├── project/          # 项目工作区组件
│   ├── editor/           # 时间线编辑器组件
│   └── assets/           # 素材相关组件
├── lib/
│   ├── api.ts            # fetch 封装
│   ├── types.ts          # TypeScript 类型
│   ├── projectIntent.ts  # 一句话意图解析（URL/画幅/时长/标题），首页与新建项目对话框共用
│   └── demoData.ts       # 仅保留 formatDuration 工具函数（演示数据已移除，见 7.5）
└── stores/
    └── authStore.ts      # Zustand 认证状态
```

### 3.3 渲染服务模块划分

```
services/renderer/
├── main.py               # FastAPI 入口，/health + /render/* 端点
├── requirements.txt      # Python 依赖
├── requirements-dev.txt  # 含 pytest
├── package.json          # HyperFrames + Remotion 依赖
├── Dockerfile            # Node 22 + Python + ffmpeg + Chromium 混合镜像
├── patch-remotion.py     # 修复 Remotion Linux 单进程参数
├── video_use/
│   └── edit_video.py     # video-use 引擎：spec → ffmpeg 剪辑（render(spec) + CLI）
├── remotion/             # Remotion 项目
│   ├── package.json
│   ├── remotion.config.ts
│   └── src/
└── tests/                # renderer 服务单元测试
```

## 4. 数据模型要点

- **User**：mock OAuth 用户，以 email 标识，cookie `session_user_id` 维系会话。`credits` 为生成次数额度（渲染完成时扣 1，0 时 402 拦截）；`PUT /auth/me` 切换 `plan` 时按套餐补足额度（`PLAN_CREDITS`：free 10 / pro 200 / enterprise 9999，演示环境无真实支付，避免「额度耗尽->升级」死局）。
- **Project**：项目，status 为 `draft | planning | generating | ready | failed`，`agent_state` 保存对话式规划状态。列表接口（`GET /projects/`）附带 `cover_url`：取项目第一张图片素材（本地静态路径优先，映射为 `/api/static/...`），供项目卡片封面使用。
- **Composition**：每个 Project 一个合成，包含 width/height/duration/fps 和 tracks。
- **Track**：类型 `video | image | audio | text | overlay`，按 index 排序。
- **Clip**：属于 Track，包含 start_time、duration、position、style、text_content，可关联 MediaAsset。
- **MediaAsset**：素材，来源 `upload | pexels | stock | generated | user_url`。
- **RenderJob**：渲染任务，status `queued | running | completed | failed`，记录 output_url 和 html_output_url。
- **Script**：脚本规划（当前代码中创建较少，模型已存在）。

## 5. 构建与运行

### 5.1 本地完整启动（推荐）

```bash
# 1. 启动全部服务
docker compose up -d --build

# 2. 运行数据库迁移
docker compose exec backend alembic upgrade head

# 3. 访问应用
open http://localhost:3000
```

> 注意：OAuth 为 mock 模式，点击即可登录。
>
> 注意：Docker 中 backend/worker/frontend 均挂载源码卷。backend 命令虽带 `--reload`，但 macOS 绑定挂载的文件变更事件不会传进容器，热重载实际不触发——改完 `backend/app/` 的 API 代码需 `docker compose restart backend`（异步任务代码还需 `docker compose restart worker`）；frontend 是 `npm run dev`（webpack 轮询模式），改动自动热更新。
>
> 注意：**renderer 容器不挂源码卷**（compose 只挂 `./data/assets`），改完 `services/renderer/` 的代码必须 `docker compose up -d --build renderer` 重建镜像才生效，`restart` 无效。镜像不含 pytest（`requirements-dev.txt` 未进 Dockerfile），容器内跑测试需先 `pip install pytest`，或按 6.3 在宿主机 venv 跑。

### 5.2 后端单独开发

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# 配置 .env（见 7.1 环境变量）
uvicorn app.main:app --reload --port 8000
```

### 5.3 前端单独开发

```bash
cd frontend
npm install
npm run dev        # http://localhost:3000
```

### 5.4 渲染服务单独开发

```bash
cd services/renderer
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt
npm install
cd remotion && npm install && cd ..
playwright install chromium
uvicorn main:app --reload --port 8001
```

## 6. 测试命令

### 6.1 后端测试

```bash
# 推荐：容器内跑（依赖 postgres/redis 服务名解析）
docker compose exec backend pytest
# 宿主机亦可（postgres 需暴露 5432，conftest 自动回退 localhost）
cd backend && source .venv/bin/activate && pytest
```

- **测试隔离（重要）**：`tests/conftest.py` 在导入 app 前把 `DATABASE_URL` 改写为独立的 `clipworks_test` 库（不存在则自动创建，`create_all` 建表）、`REDIS_URL` 指向 redis db 1（worker 只消费 db 0，测试入队的渲染任务永不被执行，稳定停在 queued）。每个测试结束自动清空所有表。**pytest 绝不写开发库**，不要再把测试指向 `clipworks`。
- `tests/test_renderer_health.py` 需要 renderer 容器在线；小内存机器（如 8GB 宿主 / Docker VM 仅 ~3.8GB）跑全量前可 `docker compose stop renderer worker` 降压，跑完再 `docker compose start renderer worker` 并补跑该文件。
- 关键测试文件：`tests/test_api.py`、`tests/test_agent.py`、`tests/test_render_task.py`、`tests/rendering/*.py`、`tests/test_celery.py`。

### 6.2 前端测试

```bash
cd frontend
npm test        # vitest --run
```

### 6.3 渲染服务测试

```bash
cd services/renderer
source .venv/bin/activate
pytest
```

### 6.4 端到端验证

```bash
# Shell 脚本：创建项目 -> 触发 Remotion 渲染 -> 校验真实 MP4
bash scripts/e2e_remotion.sh

# Playwright 浏览器级 E2E（需本地栈运行）
cd backend && source .venv/bin/activate && cd ..
python scripts/browser_e2e_check.py
```

## 7. 开发约定

### 7.1 环境变量

后端通过 `backend/app/config.py` 加载 `backend/.env`。**不要提交 .env 文件**。关键变量：

| 变量 | 说明 | 默认值 |
|---|---|---|
| `DATABASE_URL` | PostgreSQL 连接串 | `postgresql+psycopg2://clipworks:clipworks@localhost:5432/clipworks` |
| `REDIS_URL` | Redis URL | `redis://localhost:6379/0` |
| `RENDERER_URL` | 渲染服务地址 | `http://localhost:8001` |
| `KIMI_API_KEY` | Kimi API 密钥 | 无 |
| `KIMI_BASE_URL` | Kimi 兼容接口地址 | `https://api.kimi.com/coding/v1` |
| `KIMI_MODEL` | 模型名称 | `moonshot-v1-8k` |
| `PEXELS_API_KEY` | Pexels 配图密钥（可选，不配走 Picsum 兜底） | 无 |
| `EDGE_TTS_VOICE` | edge-tts 旁白音色（免密钥，需网络） | `zh-CN-XiaoxiaoNeural` |
| `ASSETS_DIR` | 素材/输出根目录 | `data/assets`（容器内 `/app/data/assets`） |

前端环境变量：

| 变量 | 说明 |
|---|---|
| `NEXT_PUBLIC_API_URL` | 后端 API 地址，默认 `http://localhost:8000` |
| `NEXT_PUBLIC_SITE_URL` | 站点根 URL（`metadataBase`，影响 OG 绝对 URL 生成），默认 `http://localhost:3000` |

### 7.2 路由与 API 前缀

- 后端路由不额外加 `/api` 前缀（Docker 中 Next.js rewrites 将 `/api/*` 代理到后端）。
- 静态文件挂载在 `/api/static`，对应 `data/assets`。

### 7.3 代码风格

- **Python**：使用标准 PEP 8；类型提示可选但新代码鼓励使用；函数/变量使用 `snake_case`。
- **TypeScript/React**：函数组件使用命名导出；文件/组件使用 PascalCase； hooks 和 stores 使用 camelCase。
- **Tailwind**：优先使用设计系统 token（如 `bg-background-base`、`text-content-primary`），避免硬编码颜色。
- **字体**：Inter / JetBrains Mono 以可变字体 woff2 本地托管在 `frontend/src/app/fonts/`，经 `layout.tsx` 的 `next/font/local` 注入 CSS 变量 `--font-sans` / `--font-mono`（tailwind `font-sans`/`font-mono` 引用）。新增字体走同一方式，不要引入 Google Fonts 网络请求。
- **主题**：深色优先，浅色由 `<html data-theme="light">` 切换；`layout.tsx` 内联脚本在 hydration 前从 `localStorage.cw_theme` 恢复，全局生效（不要再在单个页面里单独应用 `data-theme`）。
- **键盘焦点**：非 Button 的交互元素统一加 `.focus-ring` 工具类（`globals.css` 的 `@layer components`）；导航 active 态需同时设置 `aria-current="page"`。
- **注释**：复杂业务逻辑需加中文注释说明“为什么”。
- **浮层/弹窗**：所有 modal 与下拉菜单必须支持 Escape 关闭，并支持点击遮罩/菜单外部区域关闭（参考 `NewProjectDialog.tsx`、`TopBar.tsx` 的 `useEffect` 实现）。挂在 z-50 层上的浮层若不提供关闭出口，会遮挡下方页面按钮导致点击失效。
- **删除确认**：不用 `window.confirm`，用两步内联确认（参考 `AssetGrid.tsx` 的 `confirmingId`）。
- **视口高度**：用 `dvh`（`min-h-dvh`、`h-[calc(100dvh-...)]`），不用 `vh`，避免 iOS Safari 工具栏跳动。

### 7.4 Agent 与渲染降级

- Agent 模块在 LLM 失败时均有确定性 fallback：
  - `planner.py` -> `DEFAULT_PLAN`
  - `composer.py` -> `_fallback_composition`
  - `html_generator.py` -> `_fallback_html`
  - `modifier.py` -> `_deterministic_modify`（变红/字号/缩短/添加文字/删除末段/**画幅比例与竖横屏关键词**，按轴缩放 position 与字号，与 `render_task._apply_target_format` 同逻辑）-> LLM -> `_unsupported_reply`
- **修改结果带 `changed` 标记**：确定性/LLM 路径为 `True`，`_unsupported_reply` 为 `False`。agent 路由在 `changed=False` 时**不入队渲染、不扣额度**（避免「说了没改却照样出片」的假成功）；确定性画幅路径回传 `target_format`，路由同步到项目设置。
- 渲染服务按优先级链尝试：用户指定引擎 -> 默认引擎 -> 其他可处理引擎（以各 provider 的 `can_handle(request)` 为准）-> `MockProvider`。`VideoUseProvider.can_handle` 保守判定：仅当合成里存在绑定真实视频素材（非图片）的 video 轨 clip 时才接手，模板型合成始终归 remotion。
- `MockProvider` 会返回 `/api/static/sample.mp4`，用于无真实引擎时的兜底预览。
- Remotion 使用的 Chromium（Playwright 自带）通常不带 H.264/MP3/AAC 等专有解码器，因此用户上传的 MP4/MOV/MP3 等素材在渲染前会被转成 Chromium 安全的开放格式：
  - 后端 `app/services/media_proxy.py` 通过调用渲染服务的 `/render/proxy` 端点完成转码。
  - 视频被转为 WebM VP8（`*.remotion.webm`），音频被转为 Ogg Vorbis（`*.remotion.ogg`）。
  - 转码后的代理文件路径缓存在 `MediaAsset.metadata_` 的 `proxy_path` 字段中。
- `compositions.py` 在更新合成时会根据 clip 的 `start_time + duration` 自动同步 `Composition.duration`，避免 Remotion 输出比实际素材更长的黑帧/静音尾帧。
- **富方案（rich plan）**：`prompts.py` 的规划提示词要求 LLM 产出叙事弧线 + 逐镜 `narration / transition / lower_third / visual_type(product|broll|metaphor|text) / shot`；`composer.py` 将这些字段原样写进 clip 的 `style`。`DEFAULT_PLAN` 与 `_fallback_composition` 同样富化，保证无 LLM 时成片仍有转场/角标/旁白。
- **GenericComp 渲染语法**：`services/renderer/remotion/src/compositions/GenericComp.tsx` 承接富 schema：逐镜 `sceneTransition`（fade/slide/zoom）、品牌色边线 `LowerThird` 胶囊、图片 Ken Burns 缓推、文本 clip 与视觉 clip 的 lower_third 精确去重（含 overlay 轨重复角标与文本 clip 自带 lower_third 的三处去重，LLM 时间线常把同一角标写进三个地方）。旧合成（无新字段）向后兼容，按默认 fade 渲染。
- **旁白 TTS 降级链**（`app/services/tts.py`）：OpenAI 兼容 TTS（`OPENAI_API_KEY` / `TTS_API_KEY`）-> edge-tts 微软在线语音（免密钥、音质接近商用，需网络；`EDGE_TTS_VOICE` 默认 `zh-CN-XiaoxiaoNeural`）-> 本地 `espeak-ng -v cmn`（离线、确定性、机械音）-> BGM-only。`synthesize_narration` 逐段遍历整条链，首选提供者运行期失败自动落到下一个，不会让旁白整段消失。`audio_track.py` 负责把逐镜旁白与程序化 BGM 闪避混音（sidechaincompress），旁白总线先 `apad,atrim` pad 到全片时长再闪避，否则成片音轨会被截断。音轨文件固定为 `soundtrack.wav`，`build_soundtrack` 落库时按 `project_id+local_path` 复用已有 MediaAsset 行——重复渲染不会在素材库堆积同名音轨。
- **worker 并发与进度**：docker-compose 中 worker 以 `--concurrency=2` 运行（注意：渲染在单线程 renderer 服务内串行，并发主要 overlap 规划/抓取与渲染等待）；`render_task.py` 在规划/抓取/合成/音轨/HTML/渲染/QA 各阶段写 10 档进度事件到 `RenderJob.logs`。
- **Chromium 进程组收割**：渲染服务 `main.py` 的 Remotion/HyperFrames 调用均用 `start_new_session=True` 起进程组，失败/超时后 `_reap_process_group` 连 Chromium 孙进程一起 SIGKILL。Docker VM 内存 < 8GB 时，残留 Chromium 会让后续 BrowserRunner 全部超时并回退 mock——若渲染连续 fallback，先查 `docker stats` 与僵尸进程。建议 Docker Desktop 分配 ≥ 10GB。
- `composer.py` 的 `build_composition` LLM 超时为 150s（富方案 JSON 较大，90s 会在并发时双双回退）。
- **规划时长归一化**：`planner.py` 的 `_normalize_plan` 在 LLM 规划出口把各镜 duration 按原比例缩放，使总和精确等于 `plan.duration`，并把 start 重排为从 0 开始的连续轴（尾镜吃满剩余消除舍入漂移）。LLM 产出的「总时长与镜头排布不一致」在此收口，成片时长即用户 brief 时长。
- **画幅强制**：`plan_video(target_format=...)` 把项目画幅写进规划输入并在出口覆盖 `plan.format`；`render_task._apply_target_format` 作为安全网，在时间线落库前按轴比例缩放所有 clip 的 position（字号按纵向比例），LLM/已确认方案忽略画幅时也不会把 9:16 项目渲染成横屏。
- **自动配图降级链**（`app/services/stock_images.py`）：素材不足 3 张时 `render_task._build_assets` 自动补图——Pexels 主题搜索（`PEXELS_API_KEY`，source='pexels'）-> Lorem Picsum 按 query+index 确定性 seed 真实照片（source='stock'）。检索词来自 plan 的 `assets_needed`，缺失时用用户 prompt。配图失败静默降级，绝不阻断渲染。配图落盘文件名按 URL 哈希生成（`img_<sha1前10位>`，见 `services/assets.download_image`）——早期统一写 `img.jpg` 会互相覆盖丢图；展示名取检索主题写入 `MediaAsset.metadata_.name`（picsum URL 末段是「1080」这类无意义字符，前端 `AssetGrid` 按 `metadata_.name` -> URL 末段（去查询串）-> 本地文件名 顺序取名）。注意 MediaAsset 的 JSON 键是 `metadata_`（ORM 属性名），而 Composition 接口显式映射为 `metadata`，两者不同。

### 7.5 前端演示数据（已移除）

- 早期的演示兜底数据（`demoData.ts` 的 `DEMO_USER/DEMO_PROJECTS/DEMO_ASSETS` 等）已全部移除：它们会让用户在 API 失败时看到「假成功」。现各页面 API 失败时显示错误横幅或空状态。`demoData.ts` 仅保留 `formatDuration` 工具函数。
- 新增页面若无数据，展示真实空状态或错误提示，不要再引入静默 demo 回退。

### 7.6 数据库迁移

- 使用 Alembic：`backend/alembic.ini`。
- 新增模型后：
  1. 在 `backend/app/models.py` 定义模型。
  2. 在 `backend/alembic/env.py` 导入模型。
  3. 生成迁移：`alembic revision --autogenerate -m "描述"`。
  4. 应用迁移：`alembic upgrade head`。

## 8. 安全注意事项

- **.env 与密钥**：`backend/.env` 和 `frontend/.env.local` 已 gitignored，不得提交。
- **认证**：当前为 mock OAuth，仅通过 `session_user_id` cookie 识别用户，不适合生产直接使用。
- **文件上传**：`assets.py` 校验扩展名白名单与 50MB 大小限制，但上传目录可访问，需注意路径遍历（已做 `os.path.basename` 与扩展名校验）。
- **渲染路径校验**：渲染服务 `main.py` 使用 `_is_under_assets` 确保输入/输出路径均在 `ASSETS_DIR` 下，防止目录穿越。
- **CORS**：后端只允许 `http://localhost:3000`。
- **外部 URL 抓取**：`scraper.py` 与 `download_image` 访问用户提供的 URL，统一走 `services/url_safety.py` 的 SSRF 防护（协议白名单、DNS 解析拒绝内网/保留段、重定向逐跳校验、大小/Content-Type 限制）。自动配图等**我方构造的固定域名 URL** 可通过 `trusted_host_suffixes` 白名单跳过 DNS-IP 校验（兼容 fake-ip 代理把域名解析到 198.18/15 保留段的开发环境）；用户输入 URL 不传白名单，防护不受影响。
- **LLM 输出**：Agent 返回的 JSON/HTML 直接用于生成文件，生产环境需增加更严格的 schema 校验与沙箱。

## 9. 常见修改场景

### 9.1 新增后端 API

1. 在 `backend/app/routers/` 新增或修改路由文件。
2. 在 `backend/app/main.py` 中 `include_router`。
3. 更新 `backend/tests/test_api.py` 或新增测试文件。

### 9.2 新增 Agent 能力

1. 在 `backend/app/agent/prompts.py` 添加系统提示词。
2. 在 `backend/app/agent/` 中新增模块或扩展 `modifier.py`。
3. 在 `backend/app/agent/__init__.py` 导出。

### 9.3 新增渲染引擎

1. 在 `backend/app/rendering/providers/` 实现 `RenderProvider`。
2. 在 `backend/app/rendering/service.py` 的 `PROVIDERS` 列表中注册。
3. 如需服务侧支持，在 `services/renderer/main.py` 增加 `/render/xxx` 端点。
4. 添加对应测试。

### 9.4 新增前端页面/组件

1. 页面放在 `frontend/src/app/`（按 Next.js App Router 约定）。
2. 可复用组件放在 `frontend/src/components/` 对应子目录。
3. 类型补充到 `frontend/src/lib/types.ts`。
4. 新增测试放在 `frontend/tests/`。

## 10. 故障排查

- **Celery 任务未执行**：检查 `REDIS_URL` 是否可达，worker 容器是否运行。
- **渲染失败并 fallback 到 sample.mp4**：检查 renderer 服务健康 `/health`，确认 `hyperframes`/`remotion` 引擎可用。
- **前端无法连接后端**：确认 `NEXT_PUBLIC_API_URL` 与后端实际地址一致，且浏览器未跨域。
- **LLM 无响应或很慢**：检查 `KIMI_API_KEY` 是否有效；无效时会 fallback，但每个阶段会等待超时。
- **Docker Desktop 跑测试/渲染中途自己退出（日志为 exit 0 干净关闭）**：内存压力——本机 8GB 物理内存而 Docker VM 上限仅 ~3.8GB，renderer 的 Chromium 单个渲染就要 2-4GB。应对：`open -a Docker` 重启后 `docker compose up -d` 恢复；跑全量 pytest 前先 `docker compose stop renderer worker` 降压（见 6.1）；平时关掉不用的重型应用。
- **数据库表不存在**：运行 `alembic upgrade head`。
- **磁盘占用持续增长**：容器日志已设轮转上限（10m×3，compose 的 `logging` 段）。pytest/e2e 会在 DB 与 `data/assets/` 留下污染数据，定期运行 `bash scripts/cleanup_disk.sh`（默认 dry-run，`--yes` 执行：清测试项目+孤立素材+dangling 镜像，内含 VACUUM FULL 回收 DB 空间；`--dev-cache` 额外清 `frontend/.next` 与 `data/e2e_audit`）。macOS 上 `Docker.raw` 只增不缩属正常现象（稀疏文件），VM 内部释放的空间会被后续写入复用。

## 11. 参考文档

- `README.md`：快速开始与服务地址。
- `docs/design/clipworks-design.md`：设计系统、颜色、字体、间距、动画规范。
- `docs/superpowers/plans/` 与 `docs/superpowers/specs/`：产品计划与详细设计。
- `.superpowers/agent-implementation-report.md`：Agent 实现报告与已知问题。
- `.superpowers/ui-redesign-report.md`：UI 改造报告。
