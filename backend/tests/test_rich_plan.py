"""富方案（agent 能力升级）回归测试：规划/合成/分镜/旁白抽取都必须携带新 schema 字段。

覆盖：DEFAULT_PLAN 富化、_fallback_composition 把场景字段落到 clip.style/metadata、
_validate_storyboard 清洗新字段、_narration_scripts 优先用 style.narration。
均为纯函数，不碰 DB，host .venv 可直接跑。
"""

from app.agent.planner import DEFAULT_PLAN, _normalize_plan
from app.agent.composer import _fallback_composition
from app.agent.html_generator import _validate_storyboard, _storyboard_from_composition
from app.services.audio_track import _narration_scripts


def test_default_plan_carries_rich_fields():
    p = DEFAULT_PLAN
    assert p.get("style") and p.get("mood") and p.get("rhythm")
    assert p["scenes"], "DEFAULT_PLAN must keep scenes"
    for s in p["scenes"]:
        assert s.get("narration"), "每镜都要有旁白（驱动 TTS）"
        assert s.get("visual_type") in {"product", "broll", "metaphor", "text"}
        assert s.get("transition") in {"fade", "slide", "zoom"}


def test_fallback_composition_propagates_scene_fields():
    plan = {
        "title": "T",
        "format": "9:16",
        "duration": 6,
        "style": "赛博霓虹",
        "mood": "热血",
        "rhythm": "快切",
        "scenes": [
            {
                "start": 0,
                "duration": 3,
                "text": "钩子文案",
                "visual": "霓虹城市",
                "narration": "旁白一",
                "visual_type": "metaphor",
                "transition": "zoom",
                "lower_third": "LT-角标",
            }
        ],
    }
    comp = _fallback_composition(plan)
    assert comp["metadata"].get("style") == "赛博霓虹"
    assert comp["metadata"].get("mood") == "热血"
    assert comp["metadata"].get("rhythm") == "快切"

    tclips = [c for t in comp["tracks"] if t["type"] == "text" for c in t["clips"]]
    assert tclips, "expected a text clip"
    st = tclips[0]["style"]
    assert st.get("transition") == "zoom"
    assert st.get("lower_third") == "LT-角标"
    assert st.get("narration") == "旁白一"

    vclips = [c for t in comp["tracks"] if t["type"] == "video" for c in t["clips"]]
    assert vclips and vclips[0]["style"].get("visual_type") == "metaphor"
    assert vclips[0]["style"].get("transition") == "zoom"


def test_validate_storyboard_accepts_rich_fields():
    data = {
        "scenes": [
            {
                "start": 0,
                "duration": 3,
                "headline": "H",
                "subtext": "S",
                "visual": "霓虹",
                "image_index": 0,
                "narration": "N",
                "visual_type": "broll",
                "transition": "slide",
                "lower_third": "LT",
            }
        ]
    }
    scenes = _validate_storyboard(data, 10)
    assert scenes, "rich storyboard must validate"
    s0 = scenes[0]
    assert s0["narration"] == "N"
    assert s0["transition"] == "slide"
    assert s0["visual_type"] == "broll"
    assert s0["lower_third"] == "LT"


def test_storyboard_from_composition_keeps_style_fields():
    comp = {
        "duration": 6,
        "tracks": [
            {
                "type": "text",
                "clips": [
                    {
                        "start_time": 0,
                        "duration": 3,
                        "text_content": "文案",
                        "style": {"transition": "zoom", "lower_third": "LT", "narration": "N"},
                    }
                ],
            }
        ],
    }
    scenes = _storyboard_from_composition(comp, [])
    assert scenes and scenes[0]["transition"] == "zoom"
    assert scenes[0]["lower_third"] == "LT"
    assert scenes[0]["narration"] == "N"


def test_narration_scripts_cover_late_scenes_with_many_text_clips():
    """两条文本轨、每镜各 2 条文案（主文案+lower-third）时，旁白必须覆盖后半段场景。

    回归目标：旧实现先全量收集再按 start 取前 6 条，早场景的重复条目挤掉晚场景，
    旁白只覆盖前半段、混音被 sidechain 截短、视频被 mux 裁短。
    """
    headline_clips = [
        {"text_content": f"主文案{i}", "start_time": i * 3, "style": {"narration": f"旁白{i}"}}
        for i in range(5)
    ]
    lower_third_clips = [
        {"text_content": f"角标{i}", "start_time": i * 3, "style": {}}
        for i in range(5)
    ]
    comp = {
        "tracks": [
            {"type": "text", "clips": headline_clips},
            {"type": "text", "clips": lower_third_clips},
        ]
    }
    scripts = _narration_scripts(comp)
    starts = [s["start"] for s in scripts]
    # 每个场景一条、覆盖到最后一镜（start=12），且显式 narration 优先于角标文案
    assert starts == [0.0, 3.0, 6.0, 9.0, 12.0]
    assert all(s["text"].startswith("旁白") for s in scripts)


def test_narration_scripts_prefer_style_narration():
    comp = {
        "tracks": [
            {
                "type": "text",
                "clips": [
                    {"text_content": "屏幕文案", "start_time": 0, "style": {"narration": "旁白文案"}},
                    {"text_content": "无注释文案", "start_time": 3, "style": {}},
                ],
            }
        ]
    }
    scripts = _narration_scripts(comp)
    texts = [s["text"] for s in scripts]
    # 有 narration 时用旁白文案（给 TTS 念），不再念屏幕大字
    assert "旁白文案" in texts and "屏幕文案" not in texts
    # 没有 narration 时退回 text_content，保证逐镜都有可念的
    assert "无注释文案" in texts


def test_normalize_plan_scales_scenes_to_target_duration():
    """LLM 产出「总时长 30s 但镜头只排到 22s」时，必须按比例缩放到 30s。"""
    plan = {
        "title": "T",
        "duration": 30,
        "scenes": [
            {"start": 0, "duration": 4, "text": "a"},
            {"start": 4, "duration": 8, "text": "b"},
            {"start": 12, "duration": 10, "text": "c"},
        ],
    }
    out = _normalize_plan(plan)
    scenes = out["scenes"]
    assert out["duration"] == 30
    assert scenes[0]["start"] == 0
    # 连续不重叠：每镜 start 等于上一镜 end
    for prev, cur in zip(scenes, scenes[1:]):
        assert cur["start"] == round(prev["start"] + prev["duration"], 1)
    # 总时长精确命中 target
    total = scenes[-1]["start"] + scenes[-1]["duration"]
    assert total == 30
    # 比例保持：原 4:8:10 缩放后中镜约为首镜 2 倍
    assert abs(scenes[1]["duration"] / scenes[0]["duration"] - 2.0) < 0.2


def test_normalize_plan_derives_duration_when_missing():
    """plan.duration 缺失/非法时，用镜头覆盖范围作为目标，且仍连续化。"""
    plan = {
        "title": "T",
        "scenes": [
            {"start": 2, "duration": 3, "text": "a"},
            {"start": 9, "duration": 3, "text": "b"},
        ],
    }
    out = _normalize_plan(plan)
    assert out["duration"] == 12  # max(start+duration)
    assert out["scenes"][0]["start"] == 0
    assert out["scenes"][1]["start"] == 6
    assert out["scenes"][1]["duration"] == 6


def test_normalize_plan_keeps_default_plan_consistent():
    """DEFAULT_PLAN 本身必须已归一化（首镜 0 开始、连续、总和=duration）。"""
    scenes = DEFAULT_PLAN["scenes"]
    assert scenes[0]["start"] == 0
    for prev, cur in zip(scenes, scenes[1:]):
        assert cur["start"] == prev["start"] + prev["duration"]
    assert scenes[-1]["start"] + scenes[-1]["duration"] == DEFAULT_PLAN["duration"]


# ---------- target_format：成片画幅必须服从项目设置 ----------

from app.agent import planner
from app.tasks.render_task import _apply_target_format


def test_plan_video_fallback_honors_target_format(monkeypatch):
    """LLM 不可用时，DEFAULT_PLAN 兜底也必须带上用户画幅（默认是 16:9）。"""

    class _Boom:
        def __init__(self, *a, **k):
            pass

        def chat_completion_json(self, *a, **k):
            raise RuntimeError("llm down")

    monkeypatch.setattr(planner, "KimiClient", _Boom)
    plan = planner.plan_video(None, "手冲咖啡教程", target_format="9:16")
    assert plan["format"] == "9:16"
    # 不指定时保持默认
    assert planner.plan_video(None, "x")["format"] == "16:9"


def test_plan_video_overrides_llm_format(monkeypatch):
    """LLM 返回的画幅与用户设置冲突时，以用户设置为准。"""

    class _Fake:
        def __init__(self, *a, **k):
            pass

        def chat_completion_json(self, *a, **k):
            return {
                "title": "T",
                "scenes": [{"start": 0, "duration": 5, "text": "a"}],
                "duration": 5,
                "format": "16:9",
            }

    monkeypatch.setattr(planner, "KimiClient", _Fake)
    plan = planner.plan_video(None, "x", target_format="9:16")
    assert plan["format"] == "9:16"


def _comp_16x9():
    return {
        "width": 1920,
        "height": 1080,
        "tracks": [
            {
                "type": "text",
                "clips": [
                    {
                        "start_time": 0,
                        "duration": 5,
                        "position": {"x": 192, "y": 432, "width": 1536, "height": 216},
                        "style": {"fontSize": 86},
                        "text_content": "hi",
                    }
                ],
            }
        ],
    }


def test_apply_target_format_rescales_to_vertical():
    comp = _apply_target_format(_comp_16x9(), "9:16")
    assert (comp["width"], comp["height"]) == (1080, 1920)
    pos = comp["tracks"][0]["clips"][0]["position"]
    # x/width 按 0.5625 缩，y/height 按 1.7778 放
    assert pos["x"] == round(192 * 0.5625)
    assert pos["width"] == round(1536 * 0.5625)
    assert pos["y"] == round(432 * 1920 / 1080)
    assert pos["height"] == round(216 * 1920 / 1080)
    # 字号按纵向比例放大（竖屏相对高度语义）
    assert comp["tracks"][0]["clips"][0]["style"]["fontSize"] == round(86 * 1920 / 1080)


def test_apply_target_format_noop_and_unknown():
    comp = _comp_16x9()
    out = _apply_target_format(comp, "16:9")
    assert out["tracks"][0]["clips"][0]["position"]["x"] == 192
    assert _apply_target_format(_comp_16x9(), None)["width"] == 1920
    assert _apply_target_format(_comp_16x9(), "weird")["width"] == 1920
