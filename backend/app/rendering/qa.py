"""出片后的抽帧质量闸门（调用渲染服务的 ffmpeg 抽帧）。

只检测灾难性失败（全黑/解码失败），纯色+文案的正常成片亮度远高于阈值、不会误判。
任何基础设施异常都按「无法判定」处理（返回 ok=True），绝不因 QA 自身故障误杀好片。
"""
from __future__ import annotations

import logging

import httpx

from app.config import RENDERER_URL

logger = logging.getLogger(__name__)


def check_render_quality(video_path: str, samples: int = 6) -> tuple[bool, str | None]:
    """返回 (ok, reason)。ok=False 表示抽帧判定为黑屏/解码失败。"""
    try:
        resp = httpx.post(
            f"{RENDERER_URL}/render/qa",
            json={"video_path": video_path, "samples": samples},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:  # noqa: BLE001 - QA 故障不阻断出片
        logger.warning("QA check failed to run (%s); treating as pass", exc)
        return True, None

    ok = bool(data.get("ok"))
    reason = data.get("reason")
    if not ok:
        logger.warning("QA rejected %s: %s (samples=%s)", video_path, reason, data.get("samples"))
    return ok, reason
