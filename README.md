# ClipWorks 映工厂

AI 驱动的视频生成与剪辑工具。

## 快速开始

确保已安装 Docker 和 Docker Compose。

```bash
# 1. 克隆仓库
git clone <repo-url>
cd ClipWorks

# 2. 启动全部服务
docker-compose up -d --build

# 3. 运行数据库迁移
docker-compose exec backend alembic upgrade head

# 4. 访问应用
open http://localhost:3000
```

## 服务地址

- 前端：http://localhost:3000
- 后端 API：http://localhost:8000/docs
- PostgreSQL：localhost:5432
- Redis：localhost:6379

## 测试

```bash
# 后端测试
docker-compose exec backend pytest

# 前端测试
cd frontend && npm test
```

## 项目结构

- `frontend/` - Next.js 前端
- `backend/` - FastAPI 后端
- `services/renderer/` - 独立渲染服务，支持多引擎真实 MP4 输出
- `docker-compose.yml` - 本地开发环境

## 渲染引擎

`services/renderer/` 提供统一的独立渲染服务，后端通过 `RenderProvider` 接口按需调度：

- **HyperFrames** — 基于 Node.js 的 HTML/CSS 动画渲染引擎，整片一次性出片。
- **video-use** — 基于 ffmpeg 的原始素材剪辑引擎。
- **Mock** — 占位预览，用于无真实引擎时的兜底。

启动全部服务（包含 renderer）：

```bash
docker compose up --build
```

## Agent 式创作流程

首页现在是一个 Agent 对话入口：描述你的视频需求、粘贴 URL 或上传素材，AI 会先确认需求理解、再给出脚本方案与故事板，关键节点需要你确认后继续。导出页可调整分辨率、时长与质量，并实时查看渲染进度。

## 注意事项

- OAuth 登录为 mock 模式，点击即可登录。
- 视频渲染默认走 HyperFrames 整片渲染；有原始视频素材时走 video-use 剪辑。引擎不可用时自动降级到 Mock 占位视频。
- 时间线编辑器为 UI 骨架，复杂效果后续实现。
