import pytest
from app.agent.html_generator import generate_scene_html


def test_generate_scene_html_returns_html_with_headline():
    scene = {
        "start": 0,
        "duration": 5,
        "text": "ClipWorks 一句话成片",
        "visual": "深蓝科技粒子",
        "visual_type": "text",
        "shot": "特写",
        "narration": "让视频创作变得简单",
    }
    composition = {
        "width": 1920,
        "height": 1080,
        "fps": 30,
        "metadata": {"style": "赛博霓虹", "mood": "热血", "brand_color": "#00E5FF"},
    }
    assets = {}
    html = generate_scene_html(scene, composition, assets)
    assert html.startswith("<!DOCTYPE html>") or html.startswith("<html")
    assert "ClipWorks 一句话成片" in html
    assert "width: 1920px" in html or "1920" in html


def test_generate_scene_html_uses_fallback_when_scene_text_empty():
    scene = {"start": 0, "duration": 3, "text": "", "visual": "", "visual_type": "text"}
    composition = {"width": 1080, "height": 1920, "fps": 30, "metadata": {}}
    html = generate_scene_html(scene, composition, {})
    assert "<!DOCTYPE html>" in html
