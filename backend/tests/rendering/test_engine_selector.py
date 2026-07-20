from app.rendering.engine_selector import select_engine
from app.rendering.provider import RenderRequest


def test_video_use_still_priority_with_raw_assets():
    req = RenderRequest(composition={}, assets={}, raw_assets=["/tmp/a.mp4"])
    assert select_engine(req) == "video-use"


def test_selects_remotion_when_hinted():
    # engine_hint 尊重 Agent 推荐的引擎。
    req = RenderRequest(composition={}, assets={}, engine_hint="remotion")
    assert select_engine(req) == "remotion"


def test_default_returns_hybrid():
    # 默认营销视频请求走 hybrid：HF 负责单 scene 视觉动效，Remotion 负责总装/转场/音轨。
    req = RenderRequest(composition={}, assets={})
    assert select_engine(req) == "hybrid"


def test_hyperframes_keyword_respected():
    req = RenderRequest(
        composition={}, assets={}, user_prompt="use hyperframes light html"
    )
    assert select_engine(req) == "hyperframes"
