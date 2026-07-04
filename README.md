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
- `docker-compose.yml` - 本地开发环境

## 注意事项

- OAuth 登录为 mock 模式，点击即可登录。
- 视频渲染为 mock，生成进度模拟 5 秒完成。
- 时间线编辑器为 UI 骨架，复杂效果后续实现。
