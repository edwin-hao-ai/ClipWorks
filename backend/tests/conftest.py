"""pytest 全局隔离：测试只写 clipworks_test 库 + redis db 1，绝不污染开发库。

- 必须在任何 app 模块导入前改写 DATABASE_URL（database.py 在 import 时读取）。
  host 自动探测：容器内解析 postgres/redis 服务名，宿主机回退 localhost。
- 测试库不存在时自动创建（连 postgres 默认库），表结构用 Base.metadata.create_all。
- 每个测试结束后清空所有表，跨测试、跨运行零残留——
  从此 pytest 不会再往开发库留下「Render Poll Project ×65」这类污染。
"""
import os
import socket

import psycopg2
import pytest


def _resolve_host(service: str) -> str:
    try:
        socket.gethostbyname(service)
        return service
    except OSError:
        return "localhost"


_DB_HOST = _resolve_host("postgres")
_REDIS_HOST = _resolve_host("redis")
os.environ["DATABASE_URL"] = (
    f"postgresql+psycopg2://clipworks:clipworks@{_DB_HOST}:5432/clipworks_test"
)
# worker 只消费 redis db 0；测试入队到 db 1，任务永远不会被真正执行，
# 既避免 worker 误处理测试任务，又让渲染类断言稳定停在 queued。
os.environ["REDIS_URL"] = f"redis://{_REDIS_HOST}:6379/1"


def _ensure_test_database() -> None:
    conn = psycopg2.connect(
        host=_DB_HOST,
        port=5432,
        user="clipworks",
        password="clipworks",
        dbname="postgres",
    )
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = 'clipworks_test'")
            if not cur.fetchone():
                cur.execute("CREATE DATABASE clipworks_test")
    finally:
        conn.close()


_ensure_test_database()

from app.database import Base, SessionLocal, engine  # noqa: E402
import app.models  # noqa: E402,F401  # 确保所有模型注册到 metadata

Base.metadata.create_all(bind=engine)


@pytest.fixture(autouse=True)
def _clean_tables():
    yield
    db = SessionLocal()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()
    finally:
        db.close()
