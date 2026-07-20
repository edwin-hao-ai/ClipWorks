from app.rendering.engine_selector import select_engine
from app.rendering.provider import RenderRequest


def test_selects_video_use_for_raw_assets():
    req = RenderRequest(composition={}, assets={}, raw_assets=["/tmp/a.mp4"])
    assert select_engine(req) == "video-use"


def test_selects_remotion_for_template_prompt():
    req = RenderRequest(composition={}, assets={}, user_prompt="用 Remotion 模板批量生成")
    assert select_engine(req) == "remotion"


def test_defaults_to_remotion():
    # Remotion 是默认引擎：真素材/动效/H.264 天花板更高；失败由 RenderService 降级。
    req = RenderRequest(composition={}, assets={})
    assert select_engine(req) == "remotion"


def test_selects_hyperframes_when_explicitly_requested():
    req = RenderRequest(composition={}, assets={}, user_prompt="用 hyperframes 轻量 html 出片")
    assert select_engine(req) == "hyperframes"
