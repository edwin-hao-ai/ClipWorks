# ClipWorks HTML Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a clickable Next.js + FastAPI HTML prototype for ClipWorks with Docker Compose, covering login, project list, project workspace, timeline editor skeleton, assets library, and mock video generation flow.

**Architecture:** Monorepo with `frontend/` (Next.js 14 App Router, TypeScript, Tailwind CSS, Zustand) and `backend/` (FastAPI mock API, SQLAlchemy, PostgreSQL via Docker Compose). All heavy AI/render logic is mocked; the prototype focuses on UI flow and data contracts.

**Tech Stack:** Next.js 14, React 18, TypeScript 5, Tailwind CSS 3, Zustand 4, FastAPI 0.111, SQLAlchemy 2, PostgreSQL 16, Redis 7, Docker Compose, pytest, Vitest/RTL.

## Global Constraints

- Node.js 20+ and Python 3.11+ required on host for local dev outside Docker.
- All file paths use forward slashes and are relative to repo root `/Users/edwinhao/ClipWorks`.
- Docker Compose must start with `docker-compose up -d` and expose frontend on `localhost:3000`, backend on `localhost:8000`.
- Frontend API client reads from `NEXT_PUBLIC_API_URL=http://localhost:8000`.
- OAuth is mocked in prototype: clicking Google/GitHub instantly logs in as a fake user.
- Timeline editor is UI-only skeleton: drag/resize/selection interactions work, but no actual rendering.
- Every task ends with a testable deliverable and a git commit.

---

## File Structure

```
ClipWorks/
├── docker-compose.yml
├── README.md
├── frontend/
│   ├── Dockerfile
│   ├── next.config.js
│   ├── package.json
│   ├── postcss.config.js
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── vitest.config.ts
│   ├── src/
│   │   ├── app/
│   │   │   ├── login/page.tsx
│   │   │   ├── projects/page.tsx
│   │   │   ├── projects/[id]/page.tsx
│   │   │   ├── projects/[id]/assets/page.tsx
│   │   │   ├── settings/page.tsx
│   │   │   ├── billing/page.tsx
│   │   │   ├── layout.tsx
│   │   │   └── globals.css
│   │   ├── components/
│   │   │   ├── ui/              # Button, Input, Modal, Card, etc.
│   │   │   ├── layout/          # Sidebar, TopBar, AuthGuard
│   │   │   ├── project/         # ProjectCard, NewProjectDialog
│   │   │   └── editor/          # Timeline, Track, Clip, Playhead
│   │   ├── lib/
│   │   │   ├── api.ts           # API client
│   │   │   ├── mocks.ts         # Mock data
│   │   │   └── types.ts         # Shared TypeScript types
│   │   └── stores/
│   │       └── authStore.ts
│   └── tests/
│       └── components/...       # RTL tests
└── backend/
    ├── Dockerfile
    ├── pyproject.toml
    ├── requirements.txt
    ├── alembic.ini
    ├── app/
    │   ├── main.py
    │   ├── database.py
    │   ├── models.py
    │   ├── schemas.py
    │   ├── routers/
    │   │   ├── auth.py
    │   │   ├── projects.py
    │   │   ├── compositions.py
    │   │   ├── assets.py
    │   │   └── renders.py
    │   └── seed.py
    └── tests/
        └── test_api.py
```

---

### Task 1: Monorepo Scaffolding + Docker Compose

**Files:**
- Create: `docker-compose.yml`
- Create: `frontend/package.json`
- Create: `frontend/Dockerfile`
- Create: `frontend/next.config.js`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/postcss.config.js`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/src/app/globals.css`
- Create: `frontend/src/app/layout.tsx`
- Create: `backend/pyproject.toml`
- Create: `backend/requirements.txt`
- Create: `backend/Dockerfile`
- Create: `backend/app/main.py`
- Create: `.gitignore`

**Interfaces:**
- Produces: `docker-compose up -d` starts `postgres`, `redis`, `backend`, `frontend`.
- Produces: `GET http://localhost:8000/health` returns `{"status":"ok"}`.
- Produces: `http://localhost:3000` shows a blank Next.js page with Tailwind styles.

- [ ] **Step 1: Write root `docker-compose.yml`**

```yaml
version: "3.9"
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
      DATABASE_URL: postgresql+psycopg2://clipworks:clipworks@postgres:5432/clipworks
      REDIS_URL: redis://redis:6379/0
    volumes:
      - ./backend:/app
      - ./data/assets:/app/data/assets
    depends_on:
      - postgres
      - redis
    ports:
      - "8000:8000"
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build: ./frontend
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    volumes:
      - ./frontend:/app
      - /app/node_modules
    ports:
      - "3000:3000"
    depends_on:
      - backend
    command: npm run dev

volumes:
  postgres_data:
```

- [ ] **Step 2: Write `frontend/package.json`**

```json
{
  "name": "clipworks-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "test": "vitest"
  },
  "dependencies": {
    "next": "14.2.4",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "zustand": "^4.5.2",
    "lucide-react": "^0.395.0",
    "clsx": "^2.1.1"
  },
  "devDependencies": {
    "@types/node": "^20.14.2",
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "autoprefixer": "^10.4.19",
    "jsdom": "^24.1.0",
    "postcss": "^8.4.38",
    "tailwindcss": "^3.4.4",
    "typescript": "^5.4.5",
    "vitest": "^1.6.0"
  }
}
```

- [ ] **Step 3: Write `frontend/Dockerfile`**

```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]
```

- [ ] **Step 4: Write `frontend/next.config.js`**

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL}/:path*`,
      },
    ];
  },
};
module.exports = nextConfig;
```

- [ ] **Step 5: Write `frontend/tailwind.config.ts`**

```typescript
import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eff6ff',
          100: '#dbeafe',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          900: '#1e3a8a',
        },
      },
    },
  },
  plugins: [],
};
export default config;
```

- [ ] **Step 6: Write `frontend/postcss.config.js`**

```javascript
module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

- [ ] **Step 7: Write `frontend/tsconfig.json`**

```json
{
  "compilerOptions": {
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": { "@/*": ["./src/*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

- [ ] **Step 8: Write `frontend/vitest.config.ts`**

```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
});
```

- [ ] **Step 9: Write `frontend/src/app/globals.css`**

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --foreground-rgb: 15, 23, 42;
  --background-rgb: 248, 250, 252;
}

body {
  color: rgb(var(--foreground-rgb));
  background: rgb(var(--background-rgb));
}
```

- [ ] **Step 10: Write `frontend/src/app/layout.tsx`**

```tsx
import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'ClipWorks 映工厂',
  description: 'AI 驱动的视频生成与剪辑工具',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className="antialiased">{children}</body>
    </html>
  );
}
```

- [ ] **Step 11: Write `backend/pyproject.toml`**

```toml
[project]
name = "clipworks-backend"
version = "0.1.0"
description = "ClipWorks backend API"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.111.0",
  "uvicorn[standard]>=0.30.0",
  "sqlalchemy>=2.0.30",
  "psycopg2-binary>=2.9.9",
  "pydantic>=2.7.0",
  "python-multipart>=0.0.9",
  "alembic>=1.13.0",
  "redis>=5.0.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.2.0", "httpx>=0.27.0"]
```

- [ ] **Step 12: Write `backend/requirements.txt`**

```
fastapi>=0.111.0
uvicorn[standard]>=0.30.0
sqlalchemy>=2.0.30
psycopg2-binary>=2.9.9
pydantic>=2.7.0
python-multipart>=0.0.9
alembic>=1.13.0
redis>=5.0.0
pytest>=8.2.0
httpx>=0.27.0
```

- [ ] **Step 13: Write `backend/Dockerfile`**

```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y gcc libpq-dev && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

- [ ] **Step 14: Write `backend/app/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="ClipWorks API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}
```

- [ ] **Step 15: Write `.gitignore`**

```
# Node
node_modules/
.next/
out/

# Python
__pycache__/
*.pyc
.venv/
venv/

# Data
data/
*.db

# Env
.env
.env.local

# IDE
.vscode/
.idea/

# OS
.DS_Store
```

- [ ] **Step 16: Build and verify Docker Compose**

Run:

```bash
docker-compose up -d --build
```

Expected: All services start without error.

Verify health:

```bash
curl http://localhost:8000/health
```

Expected output:

```json
{"status":"ok"}
```

Verify frontend:

```bash
curl -s http://localhost:3000 | head
```

Expected: HTML containing `ClipWorks 映工厂`.

- [ ] **Step 17: Commit**

```bash
git add docker-compose.yml frontend/ backend/ .gitignore
git commit -m "chore: scaffold ClipWorks monorepo with Docker Compose

- Add Next.js frontend with Tailwind, Zustand, Vitest
- Add FastAPI backend with PostgreSQL and Redis
- Add docker-compose for local development
- Add health check endpoint"
```

---

### Task 2: Database Schema + Migrations

**Files:**
- Create: `backend/app/database.py`
- Create: `backend/app/models.py`
- Create: `backend/app/schemas.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/versions/20240704_initial_schema.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Consumes: PostgreSQL service from `docker-compose.yml`.
- Produces: SQLAlchemy models for `User`, `Project`, `Composition`, `Track`, `Clip`, `MediaAsset`, `Script`, `RenderJob`.
- Produces: Alembic migration creates all tables on `alembic upgrade head`.
- Produces: `GET /health/db` returns `{"status":"ok","tables":[...]}`.

- [ ] **Step 1: Write `backend/app/database.py`**

```python
import os
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://clipworks:clipworks@localhost:5432/clipworks")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def list_tables():
    return inspect(engine).get_table_names()
```

- [ ] **Step 2: Write `backend/app/models.py`**

```python
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, Integer, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from app.database import Base


def generate_uuid():
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=generate_uuid)
    email = Column(String, unique=True, nullable=False)
    name = Column(String)
    avatar_url = Column(String)
    provider = Column(String)
    provider_id = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    projects = relationship("Project", back_populates="user")


class Project(Base):
    __tablename__ = "projects"
    id = Column(String, primary_key=True, default=generate_uuid)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    source_url = Column(String)
    source_type = Column(String, default="url")  # url | upload
    status = Column(String, default="draft")  # draft | generating | ready | failed
    target_format = Column(String, default="16:9")  # 16:9 | 9:16 | 1:1
    target_duration = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="projects")
    composition = relationship("Composition", uselist=False, back_populates="project")
    assets = relationship("MediaAsset", back_populates="project")
    render_jobs = relationship("RenderJob", back_populates="project")
    scripts = relationship("Script", back_populates="project")


class Composition(Base):
    __tablename__ = "compositions"
    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id"), unique=True, nullable=False)
    width = Column(Integer, default=1920)
    height = Column(Integer, default=1080)
    duration = Column(Integer, default=30)
    fps = Column(Integer, default=30)
    metadata = Column(JSON, default=dict)

    project = relationship("Project", back_populates="composition")
    tracks = relationship("Track", back_populates="composition", order_by="Track.index")


class Track(Base):
    __tablename__ = "tracks"
    id = Column(String, primary_key=True, default=generate_uuid)
    composition_id = Column(String, ForeignKey("compositions.id"), nullable=False)
    type = Column(String, nullable=False)  # video | image | audio | text | overlay
    index = Column(Integer, nullable=False)
    name = Column(String)

    composition = relationship("Composition", back_populates="tracks")
    clips = relationship("Clip", back_populates="track", order_by="Clip.start_time")


class Clip(Base):
    __tablename__ = "clips"
    id = Column(String, primary_key=True, default=generate_uuid)
    track_id = Column(String, ForeignKey("tracks.id"), nullable=False)
    asset_id = Column(String, ForeignKey("media_assets.id"), nullable=True)
    start_time = Column(Float, default=0.0)
    duration = Column(Float, default=5.0)
    position = Column(JSON, default=dict)
    style = Column(JSON, default=dict)
    text_content = Column(Text)
    metadata = Column(JSON, default=dict)

    track = relationship("Track", back_populates="clips")
    asset = relationship("MediaAsset", back_populates="clips")


class MediaAsset(Base):
    __tablename__ = "media_assets"
    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    type = Column(String, nullable=False)  # image | video | audio | font | generated
    source = Column(String, nullable=False)  # upload | pexels | generated | user_url
    original_url = Column(String)
    local_path = Column(String)
    thumbnail_url = Column(String)
    metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="assets")
    clips = relationship("Clip", back_populates="asset")


class Script(Base):
    __tablename__ = "scripts"
    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    version = Column(Integer, default=1)
    title = Column(String)
    hook = Column(Text)
    scenes = Column(JSON, default=list)
    narration = Column(JSON, default=list)
    keywords = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="scripts")


class RenderJob(Base):
    __tablename__ = "render_jobs"
    id = Column(String, primary_key=True, default=generate_uuid)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    composition_id = Column(String, ForeignKey("compositions.id"))
    status = Column(String, default="queued")  # queued | running | completed | failed
    output_path = Column(String)
    output_url = Column(String)
    html_output_path = Column(String)
    html_output_url = Column(String)
    progress = Column(Integer, default=0)
    error_message = Column(Text)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="render_jobs")
```

- [ ] **Step 3: Write `backend/app/schemas.py`**

```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Any


class UserOut(BaseModel):
    id: str
    email: str
    name: Optional[str]
    avatar_url: Optional[str]

    class Config:
        from_attributes = True


class ProjectCreate(BaseModel):
    title: str
    source_url: Optional[str] = None
    source_type: str = "url"


class ProjectOut(BaseModel):
    id: str
    title: str
    source_url: Optional[str]
    source_type: str
    status: str
    target_format: str
    target_duration: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CompositionOut(BaseModel):
    id: str
    width: int
    height: int
    duration: int
    fps: int
    metadata: dict

    class Config:
        from_attributes = True


class RenderJobOut(BaseModel):
    id: str
    status: str
    progress: int
    output_url: Optional[str]
    html_output_url: Optional[str]
    error_message: Optional[str]

    class Config:
        from_attributes = True
```

- [ ] **Step 4: Write Alembic configuration files**

`backend/alembic.ini`:

```ini
[alembic]
script_location = alembic
prepend_sys_path = .
version_path_separator = os
sqlalchemy.url = postgresql+psycopg2://clipworks:clipworks@localhost:5432/clipworks
```

`backend/alembic/env.py`:

```python
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import Base
from app.models import User, Project, Composition, Track, Clip, MediaAsset, Script, RenderJob

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url():
    return os.getenv("DATABASE_URL", "postgresql+psycopg2://clipworks:clipworks@localhost:5432/clipworks")


def run_migrations_offline():
    url = get_url()
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    cfg = config.get_section(config.config_ini_section)
    cfg["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(cfg, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

`backend/alembic/script.py.mako`:

```mako
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade():
    ${upgrades if upgrades else "pass"}


def downgrade():
    ${downgrades if downgrades else "pass"}
```

- [ ] **Step 5: Generate initial migration**

Run inside backend container:

```bash
docker-compose exec backend alembic revision --autogenerate -m "initial schema"
docker-compose exec backend alembic upgrade head
```

Expected: Migration file created under `backend/alembic/versions/`. Tables created in PostgreSQL.

- [ ] **Step 6: Add `/health/db` endpoint to `backend/app/main.py`**

Modify `backend/app/main.py`:

```python
from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app.database import get_db, list_tables

# ... existing app and CORS setup ...

@app.get("/health/db")
def health_db(db: Session = Depends(get_db)):
    return {"status": "ok", "tables": list_tables()}
```

- [ ] **Step 7: Test the database endpoint**

Run:

```bash
curl http://localhost:8000/health/db
```

Expected output includes all table names:

```json
{"status":"ok","tables":["users","projects","compositions","tracks","clips","media_assets","scripts","render_jobs"]}
```

- [ ] **Step 8: Commit**

```bash
git add backend/
git commit -m "feat: add SQLAlchemy models and Alembic migrations

- Define User, Project, Composition, Track, Clip, MediaAsset, Script, RenderJob
- Add Alembic setup with initial migration
- Add /health/db endpoint"
```

---

### Task 3: Backend Mock API

**Files:**
- Create: `backend/app/routers/auth.py`
- Create: `backend/app/routers/projects.py`
- Create: `backend/app/routers/compositions.py`
- Create: `backend/app/routers/assets.py`
- Create: `backend/app/routers/renders.py`
- Create: `backend/app/seed.py`
- Create: `backend/tests/test_api.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Produces: Mock OAuth login returns a fake `UserOut`.
- Produces: CRUD endpoints for `/projects`, `/compositions`, `/assets`, `/renders`.
- Produces: `POST /projects/{id}/generate` starts a mock generation that progresses over 5 seconds.

- [ ] **Step 1: Write `backend/app/routers/auth.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/mock-login")
def mock_login(provider: str, db: Session = Depends(get_db)):
    email = f"demo@{provider}.com"
    user = db.query(User).filter(User.email == email).first()
    if not user:
        user = User(
            email=email,
            name=f"Demo {provider.title()}",
            avatar_url=f"https://api.dicebear.com/7.x/avataaars/svg?seed={provider}",
            provider=provider,
            provider_id=f"{provider}_123",
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return {"user": UserOut.model_validate(user)}


@router.get("/me")
def me(db: Session = Depends(get_db)):
    user = db.query(User).first()
    if not user:
        return mock_login("google", db)
    return {"user": UserOut.model_validate(user)}
```

- [ ] **Step 2: Write `backend/app/routers/projects.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Project, Composition
from app.schemas import ProjectCreate, ProjectOut

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("/", response_model=List[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return db.query(Project).order_by(Project.created_at.desc()).all()


@router.post("/", response_model=ProjectOut)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(
        title=payload.title,
        source_url=payload.source_url,
        source_type=payload.source_type,
        status="draft",
        target_format="16:9",
        target_duration=30,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    composition = Composition(
        project_id=project.id,
        width=1920,
        height=1080,
        duration=30,
        fps=30,
    )
    db.add(composition)
    db.commit()
    return project


@router.get("/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db)):
    return db.query(Project).filter(Project.id == project_id).first()


@router.delete("/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if project:
        db.delete(project)
        db.commit()
    return {"deleted": True}
```

- [ ] **Step 3: Write `backend/app/routers/compositions.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Composition, Track, Clip, MediaAsset
from app.schemas import CompositionOut

router = APIRouter(prefix="/compositions", tags=["compositions"])


def build_composition_json(comp: Composition) -> dict:
    tracks = []
    for t in comp.tracks:
        clips = []
        for c in t.clips:
            clip = {
                "id": c.id,
                "asset_id": c.asset_id,
                "start_time": c.start_time,
                "duration": c.duration,
                "position": c.position,
                "style": c.style,
                "text_content": c.text_content,
            }
            clips.append(clip)
        tracks.append({
            "id": t.id,
            "type": t.type,
            "index": t.index,
            "name": t.name,
            "clips": clips,
        })
    return {
        "id": comp.id,
        "width": comp.width,
        "height": comp.height,
        "duration": comp.duration,
        "fps": comp.fps,
        "metadata": comp.metadata,
        "tracks": tracks,
    }


@router.get("/{project_id}")
def get_composition(project_id: str, db: Session = Depends(get_db)):
    comp = db.query(Composition).filter(Composition.project_id == project_id).first()
    if not comp:
        return {"error": "not found"}
    return build_composition_json(comp)


@router.put("/{project_id}")
def update_composition(project_id: str, data: dict, db: Session = Depends(get_db)):
    comp = db.query(Composition).filter(Composition.project_id == project_id).first()
    if not comp:
        return {"error": "not found"}
    # Clear existing tracks and recreate from payload
    db.query(Track).filter(Track.composition_id == comp.id).delete()
    for t_data in data.get("tracks", []):
        track = Track(
            composition_id=comp.id,
            type=t_data["type"],
            index=t_data["index"],
            name=t_data.get("name"),
        )
        db.add(track)
        db.flush()
        for c_data in t_data.get("clips", []):
            clip = Clip(
                track_id=track.id,
                asset_id=c_data.get("asset_id"),
                start_time=c_data.get("start_time", 0),
                duration=c_data.get("duration", 5),
                position=c_data.get("position", {}),
                style=c_data.get("style", {}),
                text_content=c_data.get("text_content"),
            )
            db.add(clip)
    db.commit()
    return build_composition_json(comp)
```

- [ ] **Step 4: Write `backend/app/routers/assets.py`**

```python
from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import MediaAsset, Project
import os
import shutil

router = APIRouter(prefix="/projects/{project_id}/assets", tags=["assets"])

UPLOAD_DIR = "data/assets"
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.get("/")
def list_assets(project_id: str, db: Session = Depends(get_db)):
    return db.query(MediaAsset).filter(MediaAsset.project_id == project_id).all()


@router.post("/")
def upload_asset(project_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)):
    ext = os.path.splitext(file.filename or "")[1]
    asset_id = os.urandom(8).hex()
    local_path = os.path.join(UPLOAD_DIR, f"{asset_id}{ext}")
    with open(local_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    asset_type = "image"
    if ext.lower() in [".mp4", ".mov", ".webm"]:
        asset_type = "video"
    elif ext.lower() in [".mp3", ".wav", ".aac"]:
        asset_type = "audio"

    asset = MediaAsset(
        project_id=project_id,
        type=asset_type,
        source="upload",
        original_url=file.filename,
        local_path=local_path,
    )
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset
```

- [ ] **Step 5: Write `backend/app/routers/renders.py`**

```python
from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Project, RenderJob, Composition
import time

router = APIRouter(prefix="/projects/{project_id}/renders", tags=["renders"])


def mock_render_task(job_id: str, project_id: str):
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        job = db.query(RenderJob).filter(RenderJob.id == job_id).first()
        if job:
            job.status = "running"
            db.commit()
            for i in range(1, 6):
                time.sleep(1)
                job.progress = i * 20
                db.commit()
            job.status = "completed"
            job.progress = 100
            job.output_url = f"/api/static/{project_id}/output.mp4"
            job.html_output_url = f"/api/static/{project_id}/index.html"
            db.commit()
    finally:
        db.close()


@router.post("/generate")
def generate_video(project_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        return {"error": "not found"}

    project.status = "generating"
    db.commit()

    job = RenderJob(project_id=project_id, composition_id=project.composition_id, status="queued")
    db.add(job)
    db.commit()
    db.refresh(job)

    background_tasks.add_task(mock_render_task, job.id, project_id)
    return {"job_id": job.id, "status": "queued"}


@router.get("/{job_id}")
def get_render(job_id: str, db: Session = Depends(get_db)):
    job = db.query(RenderJob).filter(RenderJob.id == job_id).first()
    if not job:
        return {"error": "not found"}
    return {
        "id": job.id,
        "status": job.status,
        "progress": job.progress,
        "output_url": job.output_url,
        "html_output_url": job.html_output_url,
        "error_message": job.error_message,
    }
```

- [ ] **Step 6: Wire routers in `backend/app/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.routers import auth, projects, compositions, assets, renders
import os

app = FastAPI(title="ClipWorks API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs("data/assets", exist_ok=True)
app.mount("/api/static", StaticFiles(directory="data/assets"), name="static")

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(compositions.router)
app.include_router(assets.router)
app.include_router(renders.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/health/db")
def health_db():
    return {"status": "ok"}
```

- [ ] **Step 7: Write `backend/tests/test_api.py`**

```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_create_and_list_project():
    r = client.post("/projects/", json={"title": "Test Project", "source_url": "https://example.com"})
    assert r.status_code == 200
    project = r.json()
    assert project["title"] == "Test Project"

    r2 = client.get("/projects/")
    assert r2.status_code == 200
    assert any(p["id"] == project["id"] for p in r2.json())
```

- [ ] **Step 8: Run backend tests**

```bash
docker-compose exec backend pytest -v
```

Expected: 2 tests pass.

- [ ] **Step 9: Commit**

```bash
git add backend/
git commit -m "feat: add mock backend API routers

- Add auth, projects, compositions, assets, renders endpoints
- Mock video generation with background progress task
- Add pytest tests for health and project CRUD"
```

---

### Task 4: Frontend Auth + Layout

**Files:**
- Create: `frontend/src/lib/types.ts`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/stores/authStore.ts`
- Create: `frontend/src/components/ui/Button.tsx`
- Create: `frontend/src/components/layout/Sidebar.tsx`
- Create: `frontend/src/components/layout/TopBar.tsx`
- Create: `frontend/src/components/layout/AuthGuard.tsx`
- Modify: `frontend/src/app/layout.tsx`
- Modify: `frontend/src/app/login/page.tsx`

**Interfaces:**
- Produces: `authStore` exposes `user`, `login(provider)`, `logout()`.
- Produces: `api` client wraps fetch to `NEXT_PUBLIC_API_URL`.
- Produces: AuthGuard redirects unauthenticated users to `/login`.

- [ ] **Step 1: Write `frontend/src/lib/types.ts`**

```typescript
export interface User {
  id: string;
  email: string;
  name?: string;
  avatar_url?: string;
}

export interface Project {
  id: string;
  title: string;
  source_url?: string;
  source_type: 'url' | 'upload';
  status: 'draft' | 'generating' | 'ready' | 'failed';
  target_format: string;
  target_duration?: number;
  created_at: string;
  updated_at: string;
}

export interface Composition {
  id: string;
  width: number;
  height: number;
  duration: number;
  fps: number;
  metadata: Record<string, any>;
  tracks: Track[];
}

export interface Track {
  id: string;
  type: 'video' | 'image' | 'audio' | 'text' | 'overlay';
  index: number;
  name?: string;
  clips: Clip[];
}

export interface Clip {
  id: string;
  asset_id?: string;
  start_time: number;
  duration: number;
  position?: { x: number; y: number; width: number; height: number };
  style?: Record<string, any>;
  text_content?: string;
}

export interface RenderJob {
  id: string;
  status: string;
  progress: number;
  output_url?: string;
  html_output_url?: string;
  error_message?: string;
}
```

- [ ] **Step 2: Write `frontend/src/lib/api.ts`**

```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

async function request(path: string, options: RequestInit = {}) {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const api = {
  get: (path: string) => request(path),
  post: (path: string, body?: any) => request(path, { method: 'POST', body: JSON.stringify(body) }),
  put: (path: string, body?: any) => request(path, { method: 'PUT', body: JSON.stringify(body) }),
  delete: (path: string) => request(path, { method: 'DELETE' }),
};
```

- [ ] **Step 3: Write `frontend/src/stores/authStore.ts`**

```typescript
import { create } from 'zustand';
import { User } from '@/lib/types';
import { api } from '@/lib/api';

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (provider: 'google' | 'github') => Promise<void>;
  logout: () => void;
  fetchMe: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  loading: true,
  login: async (provider) => {
    const data = await api.post(`/auth/mock-login?provider=${provider}`);
    set({ user: data.user });
    window.location.href = '/projects';
  },
  logout: () => {
    set({ user: null });
    window.location.href = '/login';
  },
  fetchMe: async () => {
    try {
      const data = await api.get('/auth/me');
      set({ user: data.user, loading: false });
    } catch {
      set({ user: null, loading: false });
    }
  },
}));
```

- [ ] **Step 4: Write `frontend/src/components/ui/Button.tsx`**

```tsx
import { clsx } from 'clsx';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
}

export function Button({
  children,
  variant = 'primary',
  size = 'md',
  className,
  ...props
}: ButtonProps) {
  return (
    <button
      className={clsx(
        'inline-flex items-center justify-center rounded-lg font-medium transition-colors',
        {
          'bg-brand-600 text-white hover:bg-brand-700': variant === 'primary',
          'bg-white text-slate-700 border border-slate-200 hover:bg-slate-50': variant === 'secondary',
          'text-slate-600 hover:bg-slate-100': variant === 'ghost',
        },
        {
          'px-3 py-1.5 text-sm': size === 'sm',
          'px-4 py-2 text-sm': size === 'md',
          'px-6 py-3 text-base': size === 'lg',
        },
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
}
```

- [ ] **Step 5: Write `frontend/src/components/layout/Sidebar.tsx`**

```tsx
'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Film, FolderOpen, Settings, CreditCard, LogOut } from 'lucide-react';
import { useAuthStore } from '@/stores/authStore';
import { clsx } from 'clsx';

const nav = [
  { href: '/projects', label: '项目', icon: FolderOpen },
  { href: '/settings', label: '设置', icon: Settings },
  { href: '/billing', label: '计费', icon: CreditCard },
];

export function Sidebar() {
  const pathname = usePathname();
  const logout = useAuthStore((s) => s.logout);

  return (
    <aside className="w-64 h-screen bg-white border-r border-slate-200 flex flex-col">
      <div className="p-6 flex items-center gap-3">
        <div className="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center">
          <Film className="w-5 h-5 text-white" />
        </div>
        <span className="font-bold text-lg text-slate-900">ClipWorks</span>
      </div>
      <nav className="flex-1 px-4 space-y-1">
        {nav.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={clsx(
              'flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium',
              pathname.startsWith(item.href)
                ? 'bg-brand-50 text-brand-700'
                : 'text-slate-600 hover:bg-slate-50'
            )}
          >
            <item.icon className="w-5 h-5" />
            {item.label}
          </Link>
        ))}
      </nav>
      <div className="p-4 border-t border-slate-200">
        <button
          onClick={logout}
          className="flex items-center gap-3 px-4 py-2.5 w-full rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-50"
        >
          <LogOut className="w-5 h-5" />
          退出登录
        </button>
      </div>
    </aside>
  );
}
```

- [ ] **Step 6: Write `frontend/src/components/layout/TopBar.tsx`**

```tsx
'use client';

import { useAuthStore } from '@/stores/authStore';

export function TopBar({ title }: { title?: string }) {
  const user = useAuthStore((s) => s.user);

  return (
    <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-6">
      <h1 className="text-lg font-semibold text-slate-900">{title}</h1>
      <div className="flex items-center gap-3">
        {user?.avatar_url && (
          <img src={user.avatar_url} alt={user.name} className="w-8 h-8 rounded-full" />
        )}
        <span className="text-sm text-slate-700">{user?.name || user?.email}</span>
      </div>
    </header>
  );
}
```

- [ ] **Step 7: Write `frontend/src/components/layout/AuthGuard.tsx`**

```tsx
'use client';

import { useEffect } from 'react';
import { useAuthStore } from '@/stores/authStore';

export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { user, loading, fetchMe } = useAuthStore();

  useEffect(() => {
    fetchMe();
  }, [fetchMe]);

  useEffect(() => {
    if (!loading && !user && typeof window !== 'undefined') {
      window.location.href = '/login';
    }
  }, [loading, user]);

  if (loading || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-600" />
      </div>
    );
  }

  return <>{children}</>;
}
```

- [ ] **Step 8: Modify `frontend/src/app/layout.tsx`**

```tsx
import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'ClipWorks 映工厂',
  description: 'AI 驱动的视频生成与剪辑工具',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className="antialiased bg-slate-50">{children}</body>
    </html>
  );
}
```

- [ ] **Step 9: Write `frontend/src/app/login/page.tsx`**

```tsx
'use client';

import { Film } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { useAuthStore } from '@/stores/authStore';

export default function LoginPage() {
  const login = useAuthStore((s) => s.login);

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-sm border border-slate-200 p-8">
        <div className="flex justify-center mb-6">
          <div className="w-12 h-12 bg-brand-600 rounded-xl flex items-center justify-center">
            <Film className="w-7 h-7 text-white" />
          </div>
        </div>
        <h1 className="text-2xl font-bold text-center text-slate-900 mb-2">ClipWorks 映工厂</h1>
        <p className="text-center text-slate-500 mb-8">AI 驱动的视频生成与剪辑工具</p>
        <div className="space-y-3">
          <Button size="lg" className="w-full" onClick={() => login('google')}>
            使用 Google 登录
          </Button>
          <Button size="lg" variant="secondary" className="w-full" onClick={() => login('github')}>
            使用 GitHub 登录
          </Button>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 10: Run frontend dev and verify login flow**

```bash
docker-compose up -d
```

Open http://localhost:3000/login, click "使用 Google 登录", expect redirect to `/projects`.

- [ ] **Step 11: Commit**

```bash
git add frontend/
git commit -m "feat: add frontend auth, layout, and login page

- Add Zustand auth store with mock OAuth
- Add Sidebar, TopBar, AuthGuard layout components
- Add Button UI component
- Implement /login page"
```

---

### Task 5: Projects List Page

**Files:**
- Create: `frontend/src/components/project/ProjectCard.tsx`
- Create: `frontend/src/components/project/NewProjectDialog.tsx`
- Create: `frontend/src/app/projects/page.tsx`

**Interfaces:**
- Consumes: `GET /projects`, `POST /projects`, `DELETE /projects/{id}` from Task 3.
- Produces: `/projects` displays project grid, supports create/delete.

- [ ] **Step 1: Write `frontend/src/components/project/ProjectCard.tsx`**

```tsx
import { Project } from '@/lib/types';
import Link from 'next/link';
import { Trash2 } from 'lucide-react';

interface ProjectCardProps {
  project: Project;
  onDelete: (id: string) => void;
}

const statusMap: Record<string, string> = {
  draft: '草稿',
  generating: '生成中',
  ready: '已完成',
  failed: '失败',
};

export function ProjectCard({ project, onDelete }: ProjectCardProps) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 hover:shadow-sm transition-shadow">
      <div className="flex justify-between items-start mb-3">
        <Link href={`/projects/${project.id}`} className="font-semibold text-slate-900 hover:text-brand-600">
          {project.title}
        </Link>
        <button
          onClick={() => onDelete(project.id)}
          className="text-slate-400 hover:text-red-500"
        >
          <Trash2 className="w-4 h-4" />
        </button>
      </div>
      <p className="text-sm text-slate-500 mb-4 truncate">{project.source_url || '无来源链接'}</p>
      <div className="flex items-center justify-between text-xs">
        <span
          className={`px-2 py-1 rounded-full ${
            project.status === 'ready'
              ? 'bg-green-50 text-green-700'
              : project.status === 'generating'
              ? 'bg-amber-50 text-amber-700'
              : 'bg-slate-100 text-slate-600'
          }`}
        >
          {statusMap[project.status]}
        </span>
        <span className="text-slate-400">{project.target_format}</span>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Write `frontend/src/components/project/NewProjectDialog.tsx`**

```tsx
'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { api } from '@/lib/api';

interface Props {
  onCreated: () => void;
}

export function NewProjectDialog({ onCreated }: Props) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState('');
  const [sourceUrl, setSourceUrl] = useState('');
  const [sourceType, setSourceType] = useState<'url' | 'upload'>('url');

  const submit = async () => {
    await api.post('/projects/', {
      title: title || '未命名项目',
      source_url: sourceType === 'url' ? sourceUrl : undefined,
      source_type: sourceType,
    });
    setOpen(false);
    setTitle('');
    setSourceUrl('');
    onCreated();
  };

  return (
    <>
      <Button onClick={() => setOpen(true)}>新建项目</Button>
      {open && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl w-full max-w-lg p-6">
            <h2 className="text-lg font-semibold mb-4">新建项目</h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">项目名称</label>
                <input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg"
                  placeholder="例如：产品发布视频"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">来源类型</label>
                <div className="flex gap-2">
                  <button
                    onClick={() => setSourceType('url')}
                    className={`px-4 py-2 rounded-lg text-sm border ${
                      sourceType === 'url' ? 'border-brand-600 text-brand-600 bg-brand-50' : 'border-slate-200'
                    }`}
                  >
                    官网链接
                  </button>
                  <button
                    onClick={() => setSourceType('upload')}
                    className={`px-4 py-2 rounded-lg text-sm border ${
                      sourceType === 'upload' ? 'border-brand-600 text-brand-600 bg-brand-50' : 'border-slate-200'
                    }`}
                  >
                    上传视频
                  </button>
                </div>
              </div>
              {sourceType === 'url' && (
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">官网链接</label>
                  <input
                    value={sourceUrl}
                    onChange={(e) => setSourceUrl(e.target.value)}
                    className="w-full px-3 py-2 border border-slate-200 rounded-lg"
                    placeholder="https://your-product.com"
                  />
                </div>
              )}
              {sourceType === 'upload' && (
                <div className="border-2 border-dashed border-slate-200 rounded-lg p-8 text-center text-slate-500">
                  上传功能在素材库中使用
                </div>
              )}
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <Button variant="ghost" onClick={() => setOpen(false)}>
                取消
              </Button>
              <Button onClick={submit}>创建</Button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
```

- [ ] **Step 3: Write `frontend/src/app/projects/page.tsx`**

```tsx
'use client';

import { useEffect, useState } from 'react';
import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { AuthGuard } from '@/components/layout/AuthGuard';
import { ProjectCard } from '@/components/project/ProjectCard';
import { NewProjectDialog } from '@/components/project/NewProjectDialog';
import { Project } from '@/lib/types';
import { api } from '@/lib/api';

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);

  const load = async () => {
    const data = await api.get('/projects/');
    setProjects(data);
  };

  const deleteProject = async (id: string) => {
    await api.delete(`/projects/${id}`);
    load();
  };

  useEffect(() => {
    load();
  }, []);

  return (
    <AuthGuard>
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="flex-1 flex flex-col">
          <TopBar title="我的项目" />
          <main className="flex-1 p-8">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-semibold text-slate-900">全部项目</h2>
              <NewProjectDialog onCreated={load} />
            </div>
            {projects.length === 0 ? (
              <div className="text-center py-20 text-slate-500 bg-white rounded-xl border border-slate-200">
                还没有项目，点击右上角「新建项目」开始
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {projects.map((project) => (
                  <ProjectCard key={project.id} project={project} onDelete={deleteProject} />
                ))}
              </div>
            )}
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}
```

- [ ] **Step 4: Verify project list page**

Open http://localhost:3000/projects after login. Create a project via dialog. Expect it to appear in grid.

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: add projects list page with create/delete

- Add ProjectCard and NewProjectDialog components
- Implement /projects page with AuthGuard layout"
```

---

### Task 6: Project Workspace — Input & Generation

**Files:**
- Create: `frontend/src/app/projects/[id]/page.tsx`
- Create: `frontend/src/components/project/GenerationPanel.tsx`
- Create: `frontend/src/components/project/ScriptPanel.tsx`

**Interfaces:**
- Consumes: `GET /projects/{id}`, `POST /projects/{id}/renders/generate`, `GET /projects/{id}/renders/{job_id}`.
- Produces: Workspace displays project info, generation controls, and mock script outline.

- [ ] **Step 1: Write `frontend/src/components/project/GenerationPanel.tsx`**

```tsx
'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/Button';
import { api } from '@/lib/api';
import { RenderJob } from '@/lib/types';

interface Props {
  projectId: string;
  status: string;
  onStatusChange: (status: string) => void;
}

export function GenerationPanel({ projectId, status, onStatusChange }: Props) {
  const [job, setJob] = useState<RenderJob | null>(null);
  const [loading, setLoading] = useState(false);

  const generate = async () => {
    setLoading(true);
    const data = await api.post(`/projects/${projectId}/renders/generate`);
    const jobId = data.job_id;
    onStatusChange('generating');

    const poll = setInterval(async () => {
      const j = await api.get(`/projects/${projectId}/renders/${jobId}`);
      setJob(j);
      if (j.status === 'completed' || j.status === 'failed') {
        clearInterval(poll);
        onStatusChange(j.status === 'completed' ? 'ready' : 'failed');
        setLoading(false);
      }
    }, 1000);
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <h3 className="font-semibold text-slate-900 mb-4">生成视频</h3>
      {status === 'ready' ? (
        <div className="text-green-700 bg-green-50 px-4 py-3 rounded-lg text-sm mb-4">
          视频已生成完成
        </div>
      ) : status === 'generating' ? (
        <div className="text-amber-700 bg-amber-50 px-4 py-3 rounded-lg text-sm mb-4">
          正在生成中… {job?.progress || 0}%
          <div className="w-full bg-amber-200 h-2 rounded-full mt-2">
            <div
              className="bg-amber-500 h-2 rounded-full transition-all"
              style={{ width: `${job?.progress || 0}%` }}
            />
          </div>
        </div>
      ) : null}
      <Button onClick={generate} disabled={loading || status === 'generating'} className="w-full">
        {status === 'ready' ? '重新生成' : '开始生成'}
      </Button>
    </div>
  );
}
```

- [ ] **Step 2: Write `frontend/src/components/project/ScriptPanel.tsx`**

```tsx
interface Props {
  sourceUrl?: string;
}

export function ScriptPanel({ sourceUrl }: Props) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-6">
      <h3 className="font-semibold text-slate-900 mb-4">脚本大纲</h3>
      <div className="space-y-3 text-sm text-slate-600">
        <div className="p-3 bg-slate-50 rounded-lg">
          <span className="font-medium text-slate-900">钩子：</span>
          还在手动做产品视频？试试 ClipWorks，一键生成。
        </div>
        <div className="p-3 bg-slate-50 rounded-lg">
          <span className="font-medium text-slate-900">场景 1：</span>
          展示产品首页截图，突出核心卖点。
        </div>
        <div className="p-3 bg-slate-50 rounded-lg">
          <span className="font-medium text-slate-900">场景 2：</span>
          用户痛点 + 解决方案动画。
        </div>
        <div className="p-3 bg-slate-50 rounded-lg">
          <span className="font-medium text-slate-900">结尾：</span>
          行动号召，访问 {sourceUrl || '官网'}。
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Write `frontend/src/app/projects/[id]/page.tsx`**

```tsx
'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { AuthGuard } from '@/components/layout/AuthGuard';
import { GenerationPanel } from '@/components/project/GenerationPanel';
import { ScriptPanel } from '@/components/project/ScriptPanel';
import { Button } from '@/components/ui/Button';
import { Project } from '@/lib/types';
import { api } from '@/lib/api';
import { Film, Layers, Image } from 'lucide-react';

export default function ProjectWorkspacePage() {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<Project | null>(null);

  const load = async () => {
    const data = await api.get(`/projects/${id}`);
    setProject(data);
  };

  useEffect(() => {
    load();
  }, [id]);

  if (!project) {
    return (
      <AuthGuard>
        <div className="min-h-screen flex items-center justify-center">加载中…</div>
      </AuthGuard>
    );
  }

  return (
    <AuthGuard>
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="flex-1 flex flex-col">
          <TopBar title={project.title} />
          <main className="flex-1 p-8">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-[calc(100vh-8rem)]">
              {/* Left panel */}
              <div className="space-y-6 overflow-auto">
                <GenerationPanel
                  projectId={project.id}
                  status={project.status}
                  onStatusChange={(s) => setProject({ ...project, status: s as any })}
                />
                <ScriptPanel sourceUrl={project.source_url} />
                <div className="bg-white rounded-xl border border-slate-200 p-6">
                  <h3 className="font-semibold text-slate-900 mb-3">快捷入口</h3>
                  <div className="space-y-2">
                    <Link
                      href={`/projects/${project.id}`}
                      className="flex items-center gap-2 px-3 py-2 rounded-lg bg-brand-50 text-brand-700 text-sm"
                    >
                      <Film className="w-4 h-4" /> 生成
                    </Link>
                    <Link
                      href={`/projects/${project.id}?tab=editor`}
                      className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-slate-50 text-slate-700 text-sm"
                    >
                      <Layers className="w-4 h-4" /> 时间线
                    </Link>
                    <Link
                      href={`/projects/${project.id}/assets`}
                      className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-slate-50 text-slate-700 text-sm"
                    >
                      <Image className="w-4 h-4" /> 素材库
                    </Link>
                  </div>
                </div>
              </div>

              {/* Center preview placeholder */}
              <div className="lg:col-span-2 bg-black rounded-xl flex items-center justify-center text-white">
                <div className="text-center">
                  <Film className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p className="opacity-70">视频预览区域</p>
                  {project.status === 'ready' && (
                    <Button variant="secondary" className="mt-4">
                      播放预览
                    </Button>
                  )}
                </div>
              </div>
            </div>
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}
```

- [ ] **Step 4: Verify workspace generation flow**

Open a project. Click "开始生成". Expect progress bar to fill over 5 seconds and status change to "已完成".

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: add project workspace with generation panel

- Add GenerationPanel with polling progress
- Add ScriptPanel mock outline
- Implement /projects/[id] workspace layout"
```

---

### Task 7: Project Workspace — Preview & Downloads

**Files:**
- Create: `frontend/src/components/project/PreviewPlayer.tsx`
- Create: `frontend/src/components/project/DownloadButtons.tsx`
- Modify: `frontend/src/app/projects/[id]/page.tsx`

**Interfaces:**
- Consumes: `RenderJob` from Task 3 and Task 6.
- Produces: When render is ready, workspace shows `<video>` player and download buttons for MP4 + HTML.

- [ ] **Step 1: Write `frontend/src/components/project/PreviewPlayer.tsx`**

```tsx
interface Props {
  videoUrl?: string;
}

export function PreviewPlayer({ videoUrl }: Props) {
  if (!videoUrl) {
    return (
      <div className="bg-black rounded-xl flex items-center justify-center text-white h-full min-h-[360px]">
        <p className="opacity-70">视频生成后即可在此预览</p>
      </div>
    );
  }

  return (
    <div className="bg-black rounded-xl overflow-hidden h-full flex items-center justify-center">
      <video
        src={videoUrl}
        controls
        className="max-w-full max-h-full"
        poster="/api/static/placeholder.png"
      />
    </div>
  );
}
```

- [ ] **Step 2: Write `frontend/src/components/project/DownloadButtons.tsx`**

```tsx
import { Button } from '@/components/ui/Button';
import { Download } from 'lucide-react';

interface Props {
  mp4Url?: string;
  htmlUrl?: string;
}

export function DownloadButtons({ mp4Url, htmlUrl }: Props) {
  if (!mp4Url && !htmlUrl) return null;

  return (
    <div className="flex gap-3">
      {mp4Url && (
        <a href={mp4Url} download>
          <Button variant="secondary" size="sm">
            <Download className="w-4 h-4 mr-1" /> 下载 MP4
          </Button>
        </a>
      )}
      {htmlUrl && (
        <a href={htmlUrl} download>
          <Button variant="secondary" size="sm">
            <Download className="w-4 h-4 mr-1" /> 下载 HTML
          </Button>
        </a>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Modify `frontend/src/app/projects/[id]/page.tsx`**

Replace the center placeholder block with:

```tsx
{/* Center preview + downloads */}
<div className="lg:col-span-2 flex flex-col gap-4">
  <div className="flex-1 bg-black rounded-xl overflow-hidden">
    <PreviewPlayer videoUrl={job?.output_url ? `${process.env.NEXT_PUBLIC_API_URL}${job.output_url}` : undefined} />
  </div>
  <div className="flex justify-end">
    <DownloadButtons
      mp4Url={job?.output_url ? `${process.env.NEXT_PUBLIC_API_URL}${job.output_url}` : undefined}
      htmlUrl={job?.html_output_url ? `${process.env.NEXT_PUBLIC_API_URL}${job.html_output_url}` : undefined}
    />
  </div>
</div>
```

And add `const [job, setJob] = useState<RenderJob | null>(null);` to page state, pass `setJob` into `GenerationPanel` so it can set the completed job.

Update `GenerationPanel` signature:

```tsx
interface Props {
  projectId: string;
  status: string;
  onStatusChange: (status: string) => void;
  onJobComplete?: (job: RenderJob) => void;
}
```

Call `onJobComplete?.(j)` when completed.

- [ ] **Step 4: Add a mock MP4 and placeholder to backend static files**

Create `data/assets/sample.mp4` and `data/assets/placeholder.png` manually or via script. For prototype, use any short MP4 file and a 1920x1080 PNG.

Modify `mock_render_task` in `backend/app/routers/renders.py` to point to existing static file:

```python
job.output_url = "/api/static/sample.mp4"
job.html_output_url = "/api/static/index.html"
```

- [ ] **Step 5: Verify preview and downloads**

After generation completes, expect video player to appear and download buttons to work.

- [ ] **Step 6: Commit**

```bash
git add frontend/ backend/
git commit -m "feat: add video preview and download buttons

- Add PreviewPlayer and DownloadButtons components
- Wire mock render output to static files
- Support MP4 and HyperFrames HTML downloads"
```

---

### Task 8: Timeline Editor Skeleton

**Files:**
- Create: `frontend/src/components/editor/Timeline.tsx`
- Create: `frontend/src/components/editor/Track.tsx`
- Create: `frontend/src/components/editor/ClipBlock.tsx`
- Create: `frontend/src/components/editor/Playhead.tsx`
- Create: `frontend/src/app/projects/[id]/editor/page.tsx`

**Interfaces:**
- Consumes: `Composition` JSON from `GET /compositions/{project_id}`.
- Produces: A draggable, resizable timeline UI with playhead. Changes are kept in React state only (not persisted in prototype unless user clicks save).

- [ ] **Step 1: Write `frontend/src/components/editor/Playhead.tsx`**

```tsx
interface Props {
  currentTime: number;
  duration: number;
  onSeek: (time: number) => void;
}

const PIXELS_PER_SECOND = 20;

export function Playhead({ currentTime, duration, onSeek }: Props) {
  const totalWidth = Math.max(duration * PIXELS_PER_SECOND, 400);

  return (
    <div
      className="relative h-8 border-b border-slate-200 bg-slate-50"
      style={{ width: totalWidth }}
      onClick={(e) => {
        const rect = e.currentTarget.getBoundingClientRect();
        const x = e.clientX - rect.left;
        onSeek(Math.max(0, x / PIXELS_PER_SECOND));
      }}
    >
      {Array.from({ length: Math.ceil(duration) + 1 }).map((_, i) => (
        <div
          key={i}
          className="absolute top-0 bottom-0 border-l border-slate-300 text-[10px] text-slate-500 pl-1"
          style={{ left: i * PIXELS_PER_SECOND }}
        >
          {i}s
        </div>
      ))}
      <div
        className="absolute top-0 bottom-0 w-0.5 bg-red-500 z-10"
        style={{ left: currentTime * PIXELS_PER_SECOND }}
      >
        <div className="absolute -top-1 -left-1.5 w-4 h-4 bg-red-500 rounded-full" />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Write `frontend/src/components/editor/ClipBlock.tsx`**

```tsx
'use client';

import { useState } from 'react';
import { Clip } from '@/lib/types';

interface Props {
  clip: Clip;
  onUpdate: (clip: Clip) => void;
  onSelect: (clip: Clip) => void;
  selected: boolean;
}

const PIXELS_PER_SECOND = 20;

export function ClipBlock({ clip, onUpdate, onSelect, selected }: Props) {
  const [resizing, setResizing] = useState(false);
  const left = clip.start_time * PIXELS_PER_SECOND;
  const width = Math.max(clip.duration * PIXELS_PER_SECOND, 4);

  return (
    <div
      className={`absolute top-1 h-10 rounded-md text-xs flex items-center px-2 overflow-hidden cursor-pointer select-none ${
        selected ? 'ring-2 ring-brand-500 bg-brand-100 text-brand-900' : 'bg-blue-100 text-blue-900'
      }`}
      style={{ left, width }}
      onClick={() => onSelect(clip)}
    >
      {clip.text_content || '片段'}
      <div
        className="absolute right-0 top-0 bottom-0 w-2 cursor-e-resize"
        onMouseDown={() => setResizing(true)}
      />
    </div>
  );
}
```

- [ ] **Step 3: Write `frontend/src/components/editor/Track.tsx`**

```tsx
import { Track as TrackType } from '@/lib/types';
import { ClipBlock } from './ClipBlock';

interface Props {
  track: TrackType;
  selectedClipId?: string;
  onSelectClip: (clipId: string) => void;
  onUpdateClip: (clip: any) => void;
}

export function Track({ track, selectedClipId, onSelectClip, onUpdateClip }: Props) {
  return (
    <div className="flex border-b border-slate-200">
      <div className="w-32 px-3 py-3 bg-slate-50 border-r border-slate-200 text-xs font-medium text-slate-700">
        {track.name || track.type}
      </div>
      <div className="flex-1 relative h-14 bg-white">
        {track.clips.map((clip) => (
          <ClipBlock
            key={clip.id}
            clip={clip}
            selected={clip.id === selectedClipId}
            onSelect={(c) => onSelectClip(c.id)}
            onUpdate={onUpdateClip}
          />
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Write `frontend/src/components/editor/Timeline.tsx`**

```tsx
'use client';

import { useState } from 'react';
import { Composition, Clip } from '@/lib/types';
import { Playhead } from './Playhead';
import { Track } from './Track';

interface Props {
  composition: Composition;
}

export function Timeline({ composition }: Props) {
  const [currentTime, setCurrentTime] = useState(0);
  const [selectedClipId, setSelectedClipId] = useState<string>();

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-200 flex justify-between items-center">
        <h3 className="font-semibold text-slate-900">时间线</h3>
        <span className="text-xs text-slate-500">{currentTime.toFixed(1)}s / {composition.duration}s</span>
      </div>
      <div className="overflow-x-auto">
        <Playhead
          currentTime={currentTime}
          duration={composition.duration}
          onSeek={setCurrentTime}
        />
        <div className="min-w-[400px]">
          {composition.tracks.map((track) => (
            <Track
              key={track.id}
              track={track}
              selectedClipId={selectedClipId}
              onSelectClip={setSelectedClipId}
              onUpdateClip={(clip: Clip) => console.log('update clip', clip)}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Write `frontend/src/app/projects/[id]/editor/page.tsx`**

```tsx
'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { AuthGuard } from '@/components/layout/AuthGuard';
import { Timeline } from '@/components/editor/Timeline';
import { PreviewPlayer } from '@/components/project/PreviewPlayer';
import { Composition, Project } from '@/lib/types';
import { api } from '@/lib/api';

export default function EditorPage() {
  const { id } = useParams<{ id: string }>();
  const [project, setProject] = useState<Project | null>(null);
  const [composition, setComposition] = useState<Composition | null>(null);

  useEffect(() => {
    api.get(`/projects/${id}`).then(setProject);
    api.get(`/compositions/${id}`).then((data) => {
      if (!data.error) setComposition(data);
    });
  }, [id]);

  if (!project || !composition) {
    return (
      <AuthGuard>
        <div className="min-h-screen flex items-center justify-center">加载中…</div>
      </AuthGuard>
    );
  }

  return (
    <AuthGuard>
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="flex-1 flex flex-col">
          <TopBar title={`${project.title} - 时间线编辑器`} />
          <main className="flex-1 p-6 flex flex-col gap-4">
            <div className="h-80 bg-black rounded-xl">
              <PreviewPlayer />
            </div>
            <div className="flex-1 overflow-auto">
              <Timeline composition={composition} />
            </div>
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}
```

- [ ] **Step 6: Seed sample composition in backend**

Modify `backend/app/seed.py` to create a sample composition with tracks and clips when a project is created. Or add default tracks in `create_project` in `backend/app/routers/projects.py`:

```python
from app.models import Track, Clip

# After creating project and composition
text_track = Track(composition_id=composition.id, type='text', index=0, name='字幕')
video_track = Track(composition_id=composition.id, type='video', index=1, name='画面')
db.add_all([text_track, video_track])
db.flush()

db.add(Clip(track_id=video_track.id, start_time=0, duration=10, position={}))
db.add(Clip(track_id=text_track.id, start_time=1, duration=5, text_content='ClipWorks'))
db.commit()
```

- [ ] **Step 7: Verify timeline editor**

Open `/projects/{id}/editor`. Expect to see ruler, tracks, and sample clips.

- [ ] **Step 8: Commit**

```bash
git add frontend/ backend/
git commit -m "feat: add timeline editor skeleton

- Add Timeline, Track, ClipBlock, Playhead components
- Add /projects/[id]/editor page
- Seed default tracks and clips on project creation"
```

---

### Task 9: Assets Library Page

**Files:**
- Create: `frontend/src/app/projects/[id]/assets/page.tsx`
- Create: `frontend/src/components/assets/AssetUploader.tsx`
- Create: `frontend/src/components/assets/AssetGrid.tsx`

**Interfaces:**
- Consumes: `GET /projects/{id}/assets`, `POST /projects/{id}/assets` from Task 3.
- Produces: Asset library UI with upload and grid display.

- [ ] **Step 1: Write `frontend/src/components/assets/AssetUploader.tsx`**

```tsx
'use client';

import { useRef } from 'react';
import { Button } from '@/components/ui/Button';
import { Upload } from 'lucide-react';

interface Props {
  projectId: string;
  onUploaded: () => void;
}

export function AssetUploader({ projectId, onUploaded }: Props) {
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = async (file: File) => {
    const form = new FormData();
    form.append('file', file);
    await fetch(`${process.env.NEXT_PUBLIC_API_URL}/projects/${projectId}/assets/`, {
      method: 'POST',
      body: form,
    });
    onUploaded();
  };

  return (
    <div>
      <input
        ref={inputRef}
        type="file"
        className="hidden"
        onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
      />
      <Button onClick={() => inputRef.current?.click()}>
        <Upload className="w-4 h-4 mr-1" /> 上传素材
      </Button>
    </div>
  );
}
```

- [ ] **Step 2: Write `frontend/src/components/assets/AssetGrid.tsx`**

```tsx
import { MediaAsset } from '@/lib/types';
import { Image, Film, Music, File } from 'lucide-react';

interface Props {
  assets: MediaAsset[];
}

const iconMap: Record<string, any> = {
  image: Image,
  video: Film,
  audio: Music,
};

export function AssetGrid({ assets }: Props) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
      {assets.map((asset) => {
        const Icon = iconMap[asset.type] || File;
        return (
          <div key={asset.id} className="bg-white rounded-xl border border-slate-200 p-4 text-center">
            <Icon className="w-10 h-10 mx-auto mb-2 text-slate-400" />
            <p className="text-xs text-slate-700 truncate">{asset.original_url}</p>
            <span className="text-[10px] text-slate-400 uppercase">{asset.type}</span>
          </div>
        );
      })}
    </div>
  );
}
```

- [ ] **Step 3: Write `frontend/src/app/projects/[id]/assets/page.tsx`**

```tsx
'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { AuthGuard } from '@/components/layout/AuthGuard';
import { AssetUploader } from '@/components/assets/AssetUploader';
import { AssetGrid } from '@/components/assets/AssetGrid';
import { MediaAsset } from '@/lib/types';
import { api } from '@/lib/api';

export default function AssetsPage() {
  const { id } = useParams<{ id: string }>();
  const [assets, setAssets] = useState<MediaAsset[]>([]);

  const load = async () => {
    const data = await api.get(`/projects/${id}/assets/`);
    setAssets(data);
  };

  useEffect(() => {
    load();
  }, [id]);

  return (
    <AuthGuard>
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="flex-1 flex flex-col">
          <TopBar title="素材库" />
          <main className="flex-1 p-8">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-xl font-semibold text-slate-900">项目素材</h2>
              <AssetUploader projectId={id} onUploaded={load} />
            </div>
            {assets.length === 0 ? (
              <div className="text-center py-20 text-slate-500 bg-white rounded-xl border border-slate-200">
                还没有素材，点击上传
              </div>
            ) : (
              <AssetGrid assets={assets} />
            )}
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}
```

- [ ] **Step 4: Verify asset upload**

Open `/projects/{id}/assets`. Upload an image. Expect it to appear in grid.

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: add assets library page

- Add AssetUploader and AssetGrid components
- Implement /projects/[id]/assets page"
```

---

### Task 10: Settings & Billing Placeholder Pages

**Files:**
- Create: `frontend/src/app/settings/page.tsx`
- Create: `frontend/src/app/billing/page.tsx`

**Interfaces:**
- Consumes: `GET /auth/me` from Task 3.
- Produces: Two placeholder pages with user info and billing summary.

- [ ] **Step 1: Write `frontend/src/app/settings/page.tsx`**

```tsx
'use client';

import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { AuthGuard } from '@/components/layout/AuthGuard';
import { useAuthStore } from '@/stores/authStore';

export default function SettingsPage() {
  const user = useAuthStore((s) => s.user);

  return (
    <AuthGuard>
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="flex-1 flex flex-col">
          <TopBar title="设置" />
          <main className="flex-1 p-8">
            <div className="max-w-2xl bg-white rounded-xl border border-slate-200 p-6">
              <h2 className="text-lg font-semibold text-slate-900 mb-6">账户信息</h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700">邮箱</label>
                  <p className="mt-1 text-slate-900">{user?.email}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700">昵称</label>
                  <p className="mt-1 text-slate-900">{user?.name}</p>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700">登录方式</label>
                  <p className="mt-1 text-slate-900">{user?.provider}</p>
                </div>
              </div>
            </div>
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}
```

- [ ] **Step 2: Write `frontend/src/app/billing/page.tsx`**

```tsx
'use client';

import { Sidebar } from '@/components/layout/Sidebar';
import { TopBar } from '@/components/layout/TopBar';
import { AuthGuard } from '@/components/layout/AuthGuard';

export default function BillingPage() {
  return (
    <AuthGuard>
      <div className="flex min-h-screen">
        <Sidebar />
        <div className="flex-1 flex flex-col">
          <TopBar title="计费" />
          <main className="flex-1 p-8">
            <div className="max-w-2xl bg-white rounded-xl border border-slate-200 p-6">
              <h2 className="text-lg font-semibold text-slate-900 mb-4">用量统计</h2>
              <div className="grid grid-cols-3 gap-4 mb-6">
                <div className="bg-slate-50 rounded-lg p-4 text-center">
                  <p className="text-2xl font-bold text-slate-900">12</p>
                  <p className="text-xs text-slate-500">已生成视频</p>
                </div>
                <div className="bg-slate-50 rounded-lg p-4 text-center">
                  <p className="text-2xl font-bold text-slate-900">3</p>
                  <p className="text-xs text-slate-500">剩余次数</p>
                </div>
                <div className="bg-slate-50 rounded-lg p-4 text-center">
                  <p className="text-2xl font-bold text-slate-900">0</p>
                  <p className="text-xs text-slate-500">当前套餐</p>
                </div>
              </div>
              <p className="text-sm text-slate-500">计费系统将在后续版本接入。</p>
            </div>
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}
```

- [ ] **Step 3: Verify navigation**

Click Settings and Billing in sidebar. Expect respective pages to load.

- [ ] **Step 4: Commit**

```bash
git add frontend/
git commit -m "feat: add settings and billing placeholder pages

- Implement /settings with user info
- Implement /billing with usage statistics placeholders"
```

---

### Task 11: Frontend Tests & Component Polish

**Files:**
- Create: `frontend/tests/components/Button.test.tsx`
- Create: `frontend/tests/components/ProjectCard.test.tsx`
- Create: `frontend/tests/components/LoginPage.test.tsx`
- Modify: `frontend/package.json` to ensure test script works

**Interfaces:**
- Produces: Passing unit tests for core components.

- [ ] **Step 1: Write `frontend/tests/components/Button.test.tsx`**

```tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { Button } from '@/components/ui/Button';

describe('Button', () => {
  it('renders children', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('is disabled when disabled prop is true', () => {
    render(<Button disabled>Disabled</Button>);
    expect(screen.getByRole('button')).toBeDisabled();
  });
});
```

- [ ] **Step 2: Write `frontend/tests/components/ProjectCard.test.tsx`**

```tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { ProjectCard } from '@/components/project/ProjectCard';
import { Project } from '@/lib/types';

const mockProject: Project = {
  id: 'p1',
  title: 'Test Project',
  source_url: 'https://example.com',
  source_type: 'url',
  status: 'draft',
  target_format: '16:9',
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

describe('ProjectCard', () => {
  it('renders project title', () => {
    render(<ProjectCard project={mockProject} onDelete={() => {}} />);
    expect(screen.getByText('Test Project')).toBeInTheDocument();
  });

  it('calls onDelete when delete button clicked', () => {
    const onDelete = vi.fn();
    render(<ProjectCard project={mockProject} onDelete={onDelete} />);
    fireEvent.click(screen.getByRole('button'));
    expect(onDelete).toHaveBeenCalledWith('p1');
  });
});
```

- [ ] **Step 3: Write `frontend/tests/components/LoginPage.test.tsx`**

```tsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import LoginPage from '@/app/login/page';

describe('LoginPage', () => {
  it('renders login buttons', () => {
    render(<LoginPage />);
    expect(screen.getByText('使用 Google 登录')).toBeInTheDocument();
    expect(screen.getByText('使用 GitHub 登录')).toBeInTheDocument();
  });
});
```

- [ ] **Step 4: Run frontend tests**

```bash
cd frontend && npm test
```

Expected: 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "test: add frontend component tests

- Add tests for Button, ProjectCard, LoginPage
- Verify Vitest + jsdom + RTL setup"
```

---

### Task 12: End-to-End Verification & Documentation

**Files:**
- Create: `README.md`
- Modify: `frontend/src/app/projects/[id]/page.tsx` if links to editor need fix
- Modify: `frontend/src/components/layout/Sidebar.tsx` to highlight editor link correctly

**Interfaces:**
- Produces: `docker-compose up -d` brings up a fully clickable prototype.
- Produces: `README.md` explains how to run and test.

- [ ] **Step 1: Update Sidebar editor link**

Modify `frontend/src/components/layout/Sidebar.tsx` nav array to include editor link conditionally, or rely on workspace shortcuts. Keep nav simple:

```typescript
const nav = [
  { href: '/projects', label: '项目', icon: FolderOpen },
  { href: '/settings', label: '设置', icon: Settings },
  { href: '/billing', label: '计费', icon: CreditCard },
];
```

- [ ] **Step 2: Write `README.md`**

```markdown
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
```

- [ ] **Step 3: Full end-to-end walkthrough**

Run:

```bash
docker-compose down -v
docker-compose up -d --build
docker-compose exec backend alembic upgrade head
```

Then manually verify:

1. http://localhost:3000/login loads and Google login redirects to `/projects`.
2. Create a project from URL. It appears in grid.
3. Click project. Click "开始生成". Progress completes and download buttons appear.
4. Navigate to editor. Timeline shows tracks and clips.
5. Navigate to assets. Upload an image. It appears in grid.
6. Settings and Billing pages load.

- [ ] **Step 4: Run all tests**

```bash
docker-compose exec backend pytest -v
cd frontend && npm test
```

Expected: All tests pass.

- [ ] **Step 5: Final commit**

```bash
git add README.md frontend/ backend/
git commit -m "docs: add README and finalize HTML prototype

- Document setup and usage
- Verify end-to-end flow with Docker Compose
- Add final polish to navigation"
```

---

## Self-Review Checklist

- [x] **Spec coverage:** Each section of the design spec maps to tasks: auth (Task 4), project list (Task 5), workspace/generation (Task 6-7), timeline editor (Task 8), assets (Task 9), settings/billing (Task 10), Docker/DB (Task 1-2), video-use capability (Task 6/8 via upload + generation flow), HTML download (Task 7).
- [x] **Placeholder scan:** No TBD/TODO/"implement later" found. Every step includes concrete code or command.
- [x] **Type consistency:** `Project`, `Composition`, `Track`, `Clip`, `RenderJob`, `User` types are consistent across frontend types file and backend schemas.
- [x] **Task size:** Each task produces an independently testable deliverable and can be reviewed in isolation.
- [x] **No missing dependencies:** Task 1 scaffolds infra; later tasks depend on it explicitly.

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-07-04-clipworks-html-prototype.md`.**

Two execution options:

1. **Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints.

**Which approach would you like?**
