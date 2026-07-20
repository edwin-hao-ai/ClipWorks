"""HyperFrames HTML 兜底：逐镜素材图应被嵌入 <img>，无素材时退回渐变。"""

from app.agent.html_generator import _fallback_html


def _comp_with_image_clip(asset_id=None):
    clip = {"start_time": 0, "duration": 5, "position": {"x": 0, "y": 0, "width": 1080, "height": 1920}}
    if asset_id:
        clip["asset_id"] = asset_id
    return {
        "width": 1080,
        "height": 1920,
        "duration": 5,
        "fps": 30,
        "metadata": {"title": "t"},
        "tracks": [{"type": "image", "index": 0, "clips": [clip]}],
    }


def test_embeds_per_clip_image_when_asset_bound():
    comp = _comp_with_image_clip(asset_id="a1")
    html = _fallback_html(comp, {"images": {"a1": "/api/static/proj/x.jpg"}})
    assert '<img src="/api/static/proj/x.jpg"' in html
    assert "kenburns" in html  # 推镜动效关键帧存在


def test_falls_back_to_gradient_without_assets():
    comp = _comp_with_image_clip(asset_id="a1")
    html = _fallback_html(comp, {"images": {}})
    assert "/api/static/proj/x.jpg" not in html
    assert "linear-gradient" in html


def test_global_background_image_still_works():
    comp = _comp_with_image_clip(asset_id=None)
    html = _fallback_html(comp, {"background_image": "/api/static/proj/bg.jpg", "images": {}})
    assert '<img src="/api/static/proj/bg.jpg"' in html
