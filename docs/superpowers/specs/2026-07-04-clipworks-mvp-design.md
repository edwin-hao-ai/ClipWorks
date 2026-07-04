# ClipWorks（映工厂）MVP 设计规格

**版本**：v0.1 MVP 原型  
**日期**：2026-07-04  
**作者**：ClipWorks 团队  
**状态**：待实现评审

---

## 1. 产品定位

ClipWorks（映工厂）是一个面向**完全没有视频经验的小白用户**的 AI 视频生成与剪辑工具。第一期的核心目标是：

> 用户只需粘贴一个产品官网链接，系统就能自动分析网页内容、生成脚本、选配画面与音乐、渲染出一条可直接下载的营销视频。同时，系统也支持用户上传自己的原始视频素材，由 AI 自动剪辑精华片段并包装到视频中（受 [browser-use/video-use](https://github.com/browser-use/video-use) 启发）。

长期愿景是成为“AI 驱动的云端视频工厂”，覆盖生成、剪辑、素材管理、团队协作等环节。但 MVP 必须聚焦，先把“链接 → 视频”和“素材 → AI 剪辑”两条端到端链路跑通。

---

## 2. MVP 范围边界

### 2.1 必须包含（本期做）

- OAuth 登录（Google / GitHub）
- 项目列表与历史管理
- 新建项目：粘贴官网链接
- 上传 Logo / 图片 / 音乐等自有素材
- 上传原始视频素材，Agent 自动剪辑精华片段（video-use 能力轻量集成）
- Agent 自动分析网页并生成视频脚本与分镜
- Agent 决策输出格式（横竖屏、时长）
- 自动获取外部素材（图库 API）与配音（TTS）
- 调用 HyperFrames 渲染为 MP4
- 视频预览与下载
- **HyperFrames HTML 源文件下载**，方便用户二次编辑或学习
- 完整时间线编辑器 UI 骨架，支持：
  - 多轨道展示
  - 片段拖拽移动 / 缩放
  - 替换片段素材
  - 播放头 scrubbing
  - 删除片段
  - 文字 / 字幕直接编辑
- 素材库 / 资源管理页面

### 2.2 明确不做（本期不做）

- 复杂手动时间线效果：关键帧、转场动画、专业调色面板、手动音频波形剪辑、多轨道混合模式
- 多用户协作与权限
- 付费系统（保留页面与数据字段，但支付流程本期不接入）
- 移动端 App
- 实时协作与评论
- 高级 AI 视频生成（如从口播生成数字人）

> 注：AI 自动剪辑中可能包含简单的自动调色、字幕烧录、音频裁剪，这些属于“自动处理”而非“用户手动精细调整”，本期可以支持。

### 2.3 “完整原型”的定义

本期的“完整”指**产品骨架与主流程完整**：所有核心页面存在、导航完整、关键交互可点击、主流程可跑通。时间线编辑器是“完整界面 + 基础操作”，而非“专业级剪辑功能”。

---

## 3. 目标用户

- **主要用户**：完全没有视频经验的中小企业主、个体创业者、运营人员
- **使用场景**：给产品官网、活动页面、功能更新快速生成社交媒体宣传片
- **核心痛点**：不会剪视频、没有设计能力、不想学习专业软件

---

## 4. 用户旅程

```
打开 ClipWorks
  → 登录（Google / GitHub OAuth）
  → 进入项目列表
  → 点击「新建项目」
  → 选择入口：
      A. 粘贴官网链接（生成营销视频）
      B. 上传原始视频素材（AI 自动剪辑）
  → （可选）上传 Logo / 图片 / 音乐
  → 点击「生成视频」
  → Agent 分析网页或视频 → 生成脚本 / 分镜 / 风格决策
  → 系统拉取 / 生成 / 剪辑素材
  → 生成 HyperFrames HTML
  → 调用 HyperFrames 渲染 MP4
  → 进入项目工作台预览视频
  → （可选）进入时间线编辑器做简单修改
  → 下载 MP4 和 HyperFrames HTML 源文件 / 返回项目列表
```

---

## 5. 信息架构与页面结构

### 5.1 页面清单

| 页面 | 说明 |
|------|------|
| `/login` | 登录页，提供 Google / GitHub OAuth 入口 |
| `/projects` | 项目列表页，展示历史项目、创建入口 |
| `/projects/[id]` | 项目工作台，包含输入、生成进度、预览、编辑器切换 |
| `/projects/[id]/assets` | 素材库，管理本项目上传/引用的素材 |
| `/settings` | 用户设置、账户信息 |
| `/billing` | 用量与计费页面（本期占位） |

### 5.2 项目工作台布局

项目工作台采用三栏或双栏布局：

- **顶部栏**：项目名称、保存状态、预览/下载按钮
- **左侧面板**：素材库、脚本/分镜大纲、风格设置
- **中间区域**：视频预览 + 时间线编辑器
- **右侧面板**（可选）：片段属性 / 字幕编辑

---

## 6. 技术架构

### 6.1 总体架构

采用前后端分离：

```
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   Next.js Web   │      │ Python/FastAPI  │      │  HyperFrames    │
│   (Frontend)    │◄────►│   (Backend)     │◄────►│   Renderer      │
│                 │      │                 │      │  (Local CLI)    │
└─────────────────┘      └────────┬────────┘      └─────────────────┘
                                  │
                       ┌──────────┴──────────┐
                       │   LLM / Agent       │
                       │   (OpenAI / Claude) │
                       └─────────────────────┘
```

### 6.2 前端

- **框架**：Next.js 14+ App Router
- **语言**：TypeScript
- **样式**：Tailwind CSS
- **状态管理**：React Context + Zustand（MVP 阶段）
- **关键库**：
  - 时间线编辑器：自研 Canvas/DOM 组件（MVP 最小化实现）
  - 视频预览：HTML5 `<video>`
  - OAuth：NextAuth.js

### 6.3 后端

- **框架**：FastAPI（Python 3.11+）
- **数据库**：PostgreSQL（本地通过 Docker Compose 启动，开发体验好，上云直接复用）
- **ORM**：SQLModel 或 SQLAlchemy
- **任务队列**：Celery + Redis（本地通过 Docker Compose 启动）
- **Agent 编排**：
  - LLM：OpenAI GPT-4o / Claude 3.5 Sonnet
  - 工作流：LangChain / LangGraph 或纯函数调用 + Prompt 管理
- **外部服务**：
  - 网页抓取：Playwright / httpx + BeautifulSoup
  - 图库 API：Pexels / Pixabay
  - TTS：Edge TTS（免费）或 ElevenLabs
  - 生图模型：Stable Diffusion 本地 / Replicate / OpenAI DALL·E

### 6.4 渲染层

- **HyperFrames CLI**：本地调用 `npx hyperframes render`
- 输入：后端生成的 `index.html` + 素材文件
- 输出：
  - MP4 视频文件
  - HyperFrames HTML 源文件（打包供用户下载）
- 渲染任务异步执行，前端通过 WebSocket 或轮询获取进度

---

## 7. 数据模型

### 7.1 核心实体

```
User
├── id
├── email
├── name
├── avatar_url
├── provider (google/github)
├── provider_id
├── created_at
└── updated_at

Project
├── id
├── user_id
├── title
├── source_url
├── status (draft / generating / ready / failed)
├── target_format (16:9 / 9:16 / 1:1)
├── target_duration
├── created_at
├── updated_at
└── composition_id

Composition（合成 / 时间线）
├── id
├── project_id
├── width
├── height
├── duration
├── fps
├── tracks[]
└── metadata

Track（轨道）
├── id
├── composition_id
├── type (video / image / audio / text / overlay)
├── index
├── name
└── clips[]

Clip（片段）
├── id
├── track_id
├── asset_id
├── start_time
├── duration
├── position (x, y, width, height)
├── style (font, color, etc.)
├── text_content
└── metadata

MediaAsset（素材）
├── id
├── project_id
├── type (image / video / audio / font / generated)
├── source (upload / pexels / generated / user_url)
├── original_url
├── local_path
├── thumbnail_url
├── metadata
└── created_at

Script（脚本 / 文案）
├── id
├── project_id
├── version
├── title
├── hook
├── scenes[]
├── narration[]
├── keywords
└── created_at

RenderJob（渲染任务）
├── id
├── project_id
├── composition_id
├── status (queued / running / completed / failed)
├── output_path          # MP4 本地路径
├── output_url           # MP4 可下载 URL
├── html_output_path     # HyperFrames HTML 源文件路径
├── html_output_url      # HTML 源文件可下载 URL
├── progress
├── error_message
├── started_at
├── completed_at
└── created_at
```

### 7.2 Composition JSON 示例

```json
{
  "id": "comp_xxx",
  "width": 1920,
  "height": 1080,
  "duration": 45,
  "fps": 30,
  "tracks": [
    {
      "id": "track_video",
      "type": "video",
      "index": 0,
      "clips": [
        {
          "id": "clip_1",
          "asset_id": "asset_hero",
          "start_time": 0,
          "duration": 15,
          "position": { "x": 0, "y": 0, "width": 1920, "height": 1080 }
        }
      ]
    },
    {
      "id": "track_text",
      "type": "text",
      "index": 1,
      "clips": [
        {
          "id": "clip_title",
          "start_time": 1,
          "duration": 5,
          "text_content": "ClipWorks，让视频创作零门槛",
          "style": { "font": "Inter", "size": 64, "color": "#FFFFFF" }
        }
      ]
    }
  ]
}
```

---

## 8. 核心流程

### 8.1 链接生成视频流程

```
1. 用户提交 source_url + 可选素材
2. 后端创建 Project、Composition、RenderJob（状态 queued）
3. 网页抓取模块获取页面标题、描述、图片、关键文案
4. Agent 模块：
   - 分析网页内容
   - 生成 Script（标题、钩子、分镜脚本、旁白）
   - 决策目标格式（16:9 / 9:16）和时长
   - 生成素材清单（需要哪些图片/视频/音乐/配音）
5. 素材模块：
   - 用户上传素材直接进入 MediaAsset
   - 外部图片/视频调用 Pexels/Pixabay API
   - 配音调用 TTS 服务
   - 需要时调用生图模型
6. 渲染模块：
   - 根据 Composition + Script + MediaAsset 生成 HyperFrames HTML
   - 调用 HyperFrames CLI 渲染为 MP4
   - 更新 RenderJob 状态与 output_url / html_output_url
7. 前端展示预览、下载入口（MP4 + HTML 源文件）
```

### 8.2 原始视频 AI 自动剪辑流程（video-use 能力）

```
1. 用户上传原始视频素材（talking head / 教程 / 口播）
2. 后端创建 Project、Composition、RenderJob
3. 语音转录模块：
   - 调用 Whisper / ElevenLabs Scribe 生成词级时间戳
   - 识别语气词、停顿、重复片段
4. Agent 模块（video-use 风格）：
   - 阅读转录文本与关键画面帧
   - 决定保留/删除片段
   - 生成字幕样式与包装策略
5. 剪辑执行：
   - 按 Agent 决策裁剪视频
   - 自动生成字幕并烧录
   - 添加背景音乐与简单包装动画
6. 输出到 Composition，生成 HyperFrames HTML
7. 渲染 MP4，前端预览与下载
```

### 8.3 编辑器修改流程

```
1. 用户在时间线拖拽/替换/编辑片段
2. 前端实时更新 Composition JSON
3. 用户点击「重新渲染」
4. 后端重新生成 HyperFrames HTML 并渲染
5. 返回新视频
```

---

## 9. 时间线编辑器设计

### 9.1 界面分区

- **时间标尺**：秒/帧刻度，播放头可拖动
- **轨道区域**：多条轨道垂直排列（视频、图片、文字、音频）
- **片段块**：每个片段是一个彩色块，显示时长和类型
- **工具栏**：播放/暂停、缩放、撤销/重做（本期可简化）、删除

### 9.2 MVP 支持操作

- 播放头拖动与预览同步
- 片段在时间轴上拖动改变起始位置
- 片段边缘拖拽改变时长
- 片段右键/按钮删除
- 双击文字片段直接编辑文案
- 替换片段素材（从素材库选择）

### 9.3 本期不支持的复杂操作

- 关键帧动画
- 转场特效
- 多轨道混合模式
- 音频波形剪辑
- 调色与滤镜
- 速度曲线

---

## 10. Agent 编排

### 10.1 Agent 职责

Agent 是系统的“导演”，负责把用户输入转化为可渲染的视频计划：

1. **网页分析师**：抓取并提炼页面核心信息
2. **脚本写手**：根据品牌调性生成营销脚本
3. **分镜师**：把脚本拆成场景，决定每个场景的画面、文字、配音
4. **美术指导**：选择配色、字体、风格、素材
5. **素材采购员**：决定调用哪些外部 API 或生图模型

### 10.2 输出产物

Agent 最终输出：

- `Script` 对象（脚本、分镜、配音文案）
- `Composition` 对象（时间线描述）
- `MediaAsset` 清单（需要获取或生成的素材）
- 渲染所需的 `index.html`（HyperFrames 格式）

### 10.3 生图/生视频能力

- 当外部图库无法满足需求时，Agent 可调用生图模型生成画面
- 输入：场景描述、风格描述
- 输出：图片 URL 或本地文件
- 可选服务商：Replicate、OpenAI DALL·E、本地 Stable Diffusion

---

## 11. 素材与存储

### 11.1 素材来源

| 来源 | 类型 | 说明 |
|------|------|------|
| 用户上传 | 图片/视频/音频/字体 | 通过项目工作台或素材库上传 |
| AI 自动剪辑 | 视频精华片段 | 上传原始素材后，Agent 自动去废话、调色、加字幕、包装片段（video-use 能力） |
| 官网抓取 | 图片/文案 | 从 source_url 自动提取 |
| 图库 API | 图片/视频 | Pexels、Pixabay 等免费图库 |
| TTS 生成 | 音频 | Edge TTS 或 ElevenLabs |
| AI 生图 | 图片 | Stable Diffusion / DALL·E / Replicate |

### 11.2 存储策略

- **MVP 本地**：文件存在本地文件系统或 Docker Volume，数据库记录路径
- **上云迁移**：替换为 S3 / R2 / MinIO 等对象存储
- **数据库**：PostgreSQL（本地 Docker Compose + 云端 RDS/Cloud SQL 直接复用），避免 SQLite 上云后的迁移成本

---

## 12. 部署与基础设施

### 12.1 本地开发环境（Docker Compose）

MVP 提供 `docker-compose.yml`，一键启动完整本地环境：

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: clipworks
      POSTGRES_USER: clipworks
      POSTGRES_PASSWORD: clipworks
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  backend:
    build: ./backend
    environment:
      DATABASE_URL: postgresql+asyncpg://clipworks:clipworks@postgres:5432/clipworks
      REDIS_URL: redis://redis:6379/0
    volumes:
      - ./data/assets:/app/data/assets
    depends_on:
      - postgres
      - redis
    ports:
      - "8000:8000"

  worker:
    build: ./backend
    command: celery -A clipworks.tasks worker --loglevel=info
    environment:
      DATABASE_URL: postgresql+asyncpg://clipworks:clipworks@postgres:5432/clipworks
      REDIS_URL: redis://redis:6379/0
    volumes:
      - ./data/assets:/app/data/assets
      - /var/run/docker.sock:/var/run/docker.sock  # 调用本地 HyperFrames
    depends_on:
      - postgres
      - redis

  frontend:
    build: ./frontend
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    ports:
      - "3000:3000"
    depends_on:
      - backend

volumes:
  postgres_data:
```

启动命令：

```bash
docker-compose up -d
```

访问入口：

- 前端：http://localhost:3000
- 后端 API：http://localhost:8000
- PostgreSQL：localhost:5432
- Redis：localhost:6379

### 12.2 上云目标架构

```
Vercel / Cloudflare Pages  →  Next.js 前端
AWS ECS / Railway / Render →  FastAPI 后端
PostgreSQL                 →  元数据
S3 / R2                    →  素材与成片存储
AWS Lambda / ECS           →  HyperFrames 渲染任务
Celery + Redis             →  异步任务队列
```

---

## 13. 风险与取舍

### 13.1 主要风险

| 风险 | 影响 | 应对 |
|------|------|------|
| 一人同时做前端、后端、Agent、渲染，进度失控 | 高 | 严控 MVP 范围，编辑器只做骨架 |
| HyperFrames 本地渲染慢，影响体验 | 中 | 渲染异步化，前端显示进度 |
| LLM 生成脚本质量不稳定 | 高 | 用强模型（GPT-4o/Claude），增加结构化输出和重试 |
| 外部素材 API 限制/不稳定 | 中 | 多图库源备份，生图模型兜底 |
| 时间线编辑器开发量大 | 高 | 本期只做基础操作，不做复杂效果 |

### 13.2 关键取舍

- **前后端分离**：增加了集成复杂度，但 Python 更适合 AI Agent 编排，且未来前后端可独立扩展。
- **先本地后云端**：降低早期成本，但数据模型和文件存储需要预留迁移路径。
- **完整编辑器骨架**：界面完整但功能克制，避免 MVP 被编辑器拖垮。

---

## 14. 后续阶段展望

### Phase 2：增强编辑

- 关键帧动画
- 转场特效库
- 音频波形剪辑
- 更多预设模板

### Phase 3：AI 剪辑增强

- 多机位/多片段自动剪辑
- 口播去语气词、加字幕的更多参数控制
- 基于 video-use 思路的高级剪辑 Agent（多轨精剪、节奏匹配）

### Phase 4：协作与商业化

- 团队协作、评论、审批
- 付费订阅与按量计费
- API 开放与第三方集成

---

## 15. 待决策事项

1. LLM 供应商最终选择（OpenAI vs Anthropic vs 其他）
2. TTS 供应商最终选择（Edge TTS vs ElevenLabs）
3. 生图模型供应商最终选择（本地 SD vs Replicate vs DALL·E）
4. 图库 API 最终选择（Pexels vs Pixabay vs 两者）
5. 时间线编辑器是否使用现有库（如 Remotion Player、Plyr）还是完全自研
