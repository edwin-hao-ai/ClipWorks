"""#7 抽帧 QA 闸门：黑屏判不合格、正常判通过、QA 服务故障按通过放行。"""
from unittest.mock import patch, MagicMock

from app.rendering.qa import check_render_quality


def _resp(payload):
    m = MagicMock()
    m.json.return_value = payload
    m.raise_for_status.return_value = None
    return m


def test_qa_black_rejected():
    with patch("app.rendering.qa.httpx.post", return_value=_resp({"ok": False, "reason": "all sampled frames near-black (peak luminance 0 < 8)", "samples": [0, 0, 0]})):
        ok, reason = check_render_quality("/x/black.mp4")
    assert ok is False
    assert reason and "near-black" in reason


def test_qa_normal_passes():
    with patch("app.rendering.qa.httpx.post", return_value=_resp({"ok": True, "reason": None, "samples": [120, 80, 200]})):
        ok, reason = check_render_quality("/x/good.mp4")
    assert ok is True
    assert reason is None


def test_qa_infrastructure_failure_fails_open():
    with patch("app.rendering.qa.httpx.post", side_effect=RuntimeError("renderer down")):
        ok, reason = check_render_quality("/x/any.mp4")
    # QA 自身故障绝不误杀好片
    assert ok is True
    assert reason is None
