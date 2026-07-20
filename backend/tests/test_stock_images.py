"""自动配图（stock images）模块单测。

纯函数 + monkeypatch，不触碰数据库与真实网络：
download_image / persist_asset / httpx.get 均被打桩。
"""

from types import SimpleNamespace

import pytest

from app.services import stock_images
from app.services.stock_images import (
    _dimensions,
    _picsum_url,
    _seed_for,
    fetch_stock_images,
)


class _FakeDB:
    """persist_asset 被 monkeypatch 掉，这里仅占位满足签名。"""

    def add(self, obj):
        pass

    def commit(self):
        pass

    def refresh(self, obj):
        pass


def _project(fmt="16:9"):
    return SimpleNamespace(id="proj-test-1", target_format=fmt, title="测试项目")


@pytest.fixture
def fake_download(monkeypatch):
    """打桩下载与落库：记录每次调用并返回假 MediaAsset。"""

    calls = []

    def _download(url, project_id, **kwargs):
        calls.append({"url": url, "project_id": project_id})
        return f"/tmp/assets/{project_id}/stock_{len(calls)}.jpg"

    def _persist(project_id, data, db):
        return SimpleNamespace(id=f"asset-{len(calls)}", **data)

    monkeypatch.setattr(stock_images, "download_image", _download)
    monkeypatch.setattr(stock_images, "persist_asset", _persist)
    return calls


def test_seed_is_deterministic_and_varies():
    assert _seed_for("coffee", 0) == _seed_for("coffee", 0)
    assert _seed_for("coffee", 0) != _seed_for("coffee", 1)
    assert _seed_for("coffee", 0) != _seed_for("tea", 0)


def test_dimensions_follow_target_format():
    assert _dimensions(_project("9:16")) == (1080, 1920)
    assert _dimensions(_project("1:1")) == (1080, 1080)
    assert _dimensions(_project("16:9")) == (1920, 1080)
    assert _dimensions(_project(None)) == (1920, 1080)


def test_picsum_url_is_stable_and_uses_dimensions():
    url1 = _picsum_url("coffee", 0, 1080, 1920)
    url2 = _picsum_url("coffee", 0, 1080, 1920)
    assert url1 == url2
    assert url1.startswith("https://picsum.photos/seed/")
    assert url1.endswith("/1080/1920")


def test_no_key_falls_back_to_picsum(monkeypatch, fake_download):
    monkeypatch.setattr(stock_images, "PEXELS_API_KEY", None)
    assets = fetch_stock_images(_project("9:16"), ["pour over coffee"], _FakeDB(), limit=3)
    assert len(assets) == 3
    assert all(a.source == "stock" for a in assets)
    # 单 query 也能通过递增 index 拿到 3 张不同 seed 的图
    urls = [c["url"] for c in fake_download]
    assert len(set(urls)) == 3
    assert all("/1080/1920" in u for u in urls)
    # 展示名写入 metadata：picsum URL 末段是「1080」这类无意义字符，
    # 素材库必须能按检索主题显示可读名称。
    assert all(a.metadata == {"name": "pour over coffee"} for a in assets)


def test_limit_is_respected(monkeypatch, fake_download):
    monkeypatch.setattr(stock_images, "PEXELS_API_KEY", None)
    assets = fetch_stock_images(_project(), ["a", "b", "c"], _FakeDB(), limit=2)
    assert len(assets) == 2
    assert fetch_stock_images(_project(), ["a"], _FakeDB(), limit=0) == []


def test_pexels_failure_falls_back_to_picsum(monkeypatch, fake_download):
    monkeypatch.setattr(stock_images, "PEXELS_API_KEY", "fake-key")

    def _boom(*args, **kwargs):
        raise RuntimeError("network down")

    monkeypatch.setattr(stock_images.httpx, "get", _boom)
    assets = fetch_stock_images(_project(), ["coffee"], _FakeDB(), limit=2)
    assert len(assets) == 2
    assert all(a.source == "stock" for a in assets)
    assert all("picsum.photos" in a.original_url for a in assets)


def test_pexels_success_uses_pexels_source(monkeypatch, fake_download):
    monkeypatch.setattr(stock_images, "PEXELS_API_KEY", "fake-key")

    class _Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "photos": [
                    {"src": {"large2x": "https://images.pexels.com/photos/1.jpg"}},
                    {"src": {"large2x": "https://images.pexels.com/photos/2.jpg"}},
                ]
            }

    monkeypatch.setattr(stock_images.httpx, "get", lambda *a, **k: _Resp())
    assets = fetch_stock_images(_project(), ["coffee"], _FakeDB(), limit=2)
    assert len(assets) == 2
    assert all(a.source == "pexels" for a in assets)
    assert all("pexels.com" in a.original_url for a in assets)


def test_download_failure_is_skipped(monkeypatch):
    """下载失败返回 None 时不落库、不抛异常。"""
    monkeypatch.setattr(stock_images, "PEXELS_API_KEY", None)
    monkeypatch.setattr(stock_images, "download_image", lambda url, pid, **kw: None)
    monkeypatch.setattr(stock_images, "persist_asset", lambda *a, **k: pytest.fail("不应落库"))
    assert fetch_stock_images(_project(), ["coffee"], _FakeDB(), limit=2) == []


def test_stock_queries_from_plan_and_prompt():
    from app.tasks.render_task import _stock_queries

    assert _stock_queries({"assets_needed": ["咖啡豆特写", "  ", "手冲壶"]}, None) == ["咖啡豆特写", "手冲壶"]
    assert _stock_queries({"assets_needed": "not-a-list"}, "手冲咖啡教程") == ["手冲咖啡教程"]
    assert _stock_queries(None, "  ") is None
    assert _stock_queries(None, None) is None
