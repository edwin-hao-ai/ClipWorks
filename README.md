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

- **HyperFrames** — 基于 Node.js 的 HTML/CSS 动画渲染引擎。
- **Remotion** — 基于 React 组件的模板视频渲染引擎。
- **video-use** — 基于浏览器自动化和原始素材的剪辑引擎。

启动全部服务（包含 renderer）：

```bash
docker compose up --build
```

## 注意事项

- OAuth 登录为 mock 模式，点击即可登录。
- 视频渲染已接入真实多引擎流水线，失败时会自动降级到 mock 渲染。
- 时间线编辑器为 UI 骨架，复杂效果后续实现。
