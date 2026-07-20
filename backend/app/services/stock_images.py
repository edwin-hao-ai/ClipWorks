"""无素材项目的自动配图：real-when-available + 确定性兜底。

「一句话成片」场景下项目没有任何上传图、也没有可抓取的官网，画面只能渲染渐变
文字卡。本模块在素材不足时按主题自动补图，降级链与 TTS 一致：

1. 配置了 PEXELS_API_KEY 时，按查询词调用 Pexels 搜索接口，下载与主题相关的
   真实照片（source='pexels'）；
2. 无密钥（或 Pexels 调用失败/无结果）时退到 Lorem Picsum——免密钥、按 seed
   确定性返回 Unsplash 真实照片（source='stock'），同一 brief 重复渲染结果稳定。

任何失败都静默降级、绝不阻断渲染主流程。
"""

import hashlib
import logging
import os
from typing import Optional

import httpx

from app.config import PEXELS_API_KEY
from app.services.assets import download_image, persist_asset

logger = logging.getLogger(__name__)

PEXELS_SEARCH_URL = "https://api.pexels.com/v1/search"

# 自动配图 URL 全由我方构造或来自 Pexels API，域名固定可信；白名单用于跳过
# DNS-IP 校验（fake-ip 代理会把域名解析到 198.18/15 保留段导致误杀）。
# 用户输入 URL 不走此白名单，SSRF 防护不受影响。
TRUSTED_HOST_SUFFIXES = ("picsum.photos", "images.pexels.com")


def _seed_for(query: str, index: int) -> str:
    """同一 query+index 生成稳定 seed，保证 picsum 兜底在重复渲染时拿到同一张图。"""
    digest = hashlib.md5(f"clipworks|{query}|{index}".encode("utf-8")).hexdigest()[:12]
    return f"cw-{digest}"


def _dimensions(project) -> tuple[int, int]:
    fmt = getattr(project, "target_format", None) or "16:9"
    return {"9:16": (1080, 1920), "1:1": (1080, 1080)}.get(fmt, (1920, 1080))


def _picsum_url(query: str, index: int, width: int, height: int) -> str:
    return f"https://picsum.photos/seed/{_seed_for(query, index)}/{width}/{height}"


def _pexels_urls(query: str, per_page: int = 2) -> list[str]:
    """Pexels 主题搜索，返回大图 URL 列表；无密钥或失败返回空列表。"""
    if not PEXELS_API_KEY:
        return []
    try:
        resp = httpx.get(
            PEXELS_SEARCH_URL,
            params={"query": query, "per_page": per_page},
            headers={"Authorization": PEXELS_API_KEY},
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            p["src"]["large2x"]
            for p in data.get("photos", [])
            if p.get("src", {}).get("large2x")
        ]
    except Exception as exc:  # noqa: BLE001 - 配图是增强，失败静默降级
        logger.warning("pexels search failed for %r: %s", query, exc)
        return []


def _persist_downloaded(project, url: str, source: str, db, name: Optional[str] = None) -> Optional[object]:
    local = download_image(url, project.id, trusted_host_suffixes=TRUSTED_HOST_SUFFIXES)
    if not local:
        return None
    try:
        data = {
            "type": "image",
            "source": source,
            "original_url": url,
            "local_path": local.replace(os.path.sep, "/"),
        }
        if name:
            # 展示名写进 metadata：picsum URL 末段是「1080」这类无意义字符，
            # 素材库需要按检索主题显示可读的名称。
            data["metadata"] = {"name": name}
        return persist_asset(project.id, data, db)
    except Exception as exc:  # noqa: BLE001
        logger.warning("persist stock asset failed %s: %s", url, exc)
        return None


def fetch_stock_images(project, queries: list[str], db, limit: int = 5) -> list:
    """按查询词自动配图并落库，返回 MediaAsset 列表。

    有 Pexels 密钥先按主题搜索；密钥缺失或 Pexels 颗粒无收时，用 Lorem Picsum
    按查询词 seed 兜底，保证至少拿到真实照片而不是渐变块。
    """
    if limit <= 0:
        return []
    if not queries:
        queries = [getattr(project, "title", "") or "product marketing"]
    width, height = _dimensions(project)

    assets: list = []
    seen_urls: set = set()

    # 1) Pexels 主题配图（real-when-available）
    if PEXELS_API_KEY:
        for query in queries:
            if len(assets) >= limit:
                break
            for url in _pexels_urls(query, per_page=min(2, limit - len(assets))):
                if len(assets) >= limit or url in seen_urls:
                    continue
                seen_urls.add(url)
                media = _persist_downloaded(project, url, "pexels", db, name=query)
                if media is not None:
                    assets.append(media)

    # 2) Pexels 无结果/无密钥 → Lorem Picsum 确定性真实照片兜底
    #    query 循环复用、index 递增，保证单 query 也能补齐 limit 张不同 seed 的图。
    if len(assets) < limit:
        for qi in range(limit - len(assets)):
            query = queries[qi % len(queries)]
            url = _picsum_url(query, qi, width, height)
            if url in seen_urls:
                continue
            seen_urls.add(url)
            media = _persist_downloaded(project, url, "stock", db, name=query)
            if media is not None:
                assets.append(media)

    return assets
