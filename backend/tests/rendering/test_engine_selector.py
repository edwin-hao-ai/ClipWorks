from app.rendering.engine_selector import select_engine
from app.rendering.provider import RenderRequest


def test_video_use_still_priority_with_raw_assets():
    req = RenderRequest(composition={}, assets={}, raw_assets=["/tmp/a.mp4"])
    assert select_engine(req) == "video-use"


def test_selects_remotion_when_hinted():
    # engine_hint 尊重 Agent 推荐的引擎。
    req = RenderRequest(composition={}, assets={}, engine_hint="remotion")
    assert select_engine(req) == "remotion"


def test_select_engine_defaults_to_hyperframes():
    # 默认整片使用 HyperFrames 渲染；Remotion 不再作为默认路径。
    req = RenderRequest(composition={}, assets={})
    assert select_engine(req) == "hyperframes"


def test_hyperframes_keyword_respected():
    req = RenderRequest(
        composition={}, assets={}, user_prompt="use hyperframes light html"
    )
    assert select_engine(req) == "hyperframes"
