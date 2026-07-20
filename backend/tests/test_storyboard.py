"""#5 结构化分镜：schema 校验 + 本地分镜构造 + 模板渲染（离线，不依赖 Kimi）。"""
from app.agent.html_generator import (
    _render_storyboard,
    _storyboard_from_composition,
    _validate_storyboard,
    generate_html,
)


COMP = {
    "width": 1080,
    "height": 1920,
    "duration": 12,
    "fps": 30,
    "metadata": {"title": "X"},
    "tracks": [
        {
            "type": "image",
            "index": 0,
            "clips": [
                {"start_time": 0, "duration": 4, "style": {"visual": "深蓝科技粒子"}},
                {"start_time": 4, "duration": 4, "style": {"visual": "暖橙日出"}},
                {"start_time": 8, "duration": 4, "style": {"visual": "森林绿"}},
            ],
        },
        {
            "type": "text",
            "index": 1,
            "clips": [
                {"start_time": 0, "duration": 4, "text_content": "世界再吵，一键静下来"},
                {"start_time": 4, "duration": 4, "text_content": "40dB 主动降噪"},
                {"start_time": 8, "duration": 4, "text_content": "36 小时续航"},
            ],
        },
    ],
}

ASSETS = {
    "image_ids": ["a1", "a2", "a3"],
    "images": {
        "a1": "/api/static/p/a1.png",
        "a2": "/api/static/p/a2.png",
        "a3": "/api/static/p/a3.png",
    },
}


def test_validate_storyboard_accepts_valid():
    good = {"scenes": [{"start": 0, "duration": 4, "headline": "hi", "image_index": 0}]}
    scenes = _validate_storyboard(good, 12)
    assert scenes and scenes[0]["headline"] == "hi"
    assert scenes[0]["image_index"] == 0


def test_validate_storyboard_rejects_invalid():
    assert _validate_storyboard({"scenes": []}, 12) is None
    assert _validate_storyboard({"scenes": [{"start": 0, "duration": 0}]}, 12) is None
    assert _validate_storyboard({"scenes": "nope"}, 12) is None
    assert _validate_storyboard(None, 12) is None


def test_storyboard_from_composition_uses_text_and_images():
    sb = _storyboard_from_composition(COMP, ASSETS["image_ids"])
    assert len(sb) == 3
    assert sb[0]["headline"] == "世界再吵，一键静下来"
    # 图片按场景循环分配
    assert sb[0]["image_index"] == 0 and sb[1]["image_index"] == 1
    # 文案按时间排序
    assert [s["start"] for s in sb] == [0.0, 4.0, 8.0]


def test_render_storyboard_embeds_images_and_copy():
    sb = _storyboard_from_composition(COMP, ASSETS["image_ids"])
    html = _render_storyboard(sb, COMP, ASSETS)
    assert "<html" in html
    assert "世界再吵" in html
    assert "/api/static/p/a1.png" in html
    assert "kenburns" in html  # 电影感推镜


def test_generate_html_offline_returns_valid_html():
    # AI 不可用（无密钥）时走本地分镜，产物仍是合法 HTML，且不触发「fallback」。
    out = generate_html(COMP, ASSETS)
    assert "<html" in out
    assert "世界再吵" in out
