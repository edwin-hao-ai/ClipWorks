from app.rendering.engine_selector import select_engine
from app.rendering.provider import RenderRequest


def test_selects_video_use_for_raw_assets():
    req = RenderRequest(composition={}, assets={}, raw_assets=["/tmp/a.mp4"])
    assert select_engine(req) == "video-use"


def test_selects_remotion_for_template_prompt():
    req = RenderRequest(composition={}, assets={}, user_prompt="用 Remotion 模板批量生成")
    assert select_engine(req) == "remotion"


def test_defaults_to_hyperframes():
    req = RenderRequest(composition={}, assets={})
    assert select_engine(req) == "hyperframes"
