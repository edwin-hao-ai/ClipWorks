from app.agent.conversation import build_fallback_plan


def fallback_script(project):
    """Return a deterministic script when no LLM is available.

    ``build_fallback_plan`` defaults to 20 s when ``project.target_duration``
    is None; the wizard brief expects 30 s, so we override via
    ``project.target_duration or 30`` when the fallback plan does not already
    carry a duration.
    """
    plan = build_fallback_plan(project)
    return {
        "title": plan.get("title", project.title),
        "hook": plan.get("hook", ""),
        "roles": [{"name": "旁白", "perspective": "品牌方"}],
        "narrative_arc": "钩子 → 痛点 → 产品登场 → 体验证据 → CTA",
        "cta": "立即体验",
        "duration": plan.get("duration", project.target_duration or 30),
        "format": plan.get("format", project.target_format or "16:9"),
    }


def fallback_assets(project, state):
    script = state.get("script", {})
    title = script.get("title", project.title)
    return {
        "needed": [
            {"type": "image", "description": f"{title} 主题配图", "query": title, "count": 1},
            {"type": "image", "description": "品牌背景", "query": "modern abstract gradient background", "count": 1},
            {"type": "music", "description": "背景音乐", "query": "upbeat background music", "count": 1},
        ]
    }


def fallback_scenes(project, state):
    plan = build_fallback_plan(project)
    scenes = plan.get("scenes", [])
    for i, s in enumerate(scenes):
        s.setdefault("visual_type", "text")
        s.setdefault("shot", "定格")
        s.setdefault("transition", "fade")
        s.setdefault("lower_third", "")
        s.setdefault("required_assets", [])
    return {"scenes": scenes}


def fallback_effects(project, state):
    scenes = state.get("scenes", {}).get("scenes", [])
    effects = []
    for i, scene in enumerate(scenes):
        visual = scene.get("visual", "")
        keywords = ["淡入"]
        if "科技" in visual or "tech" in visual.lower():
            keywords.append("粒子")
        if "暖" in visual:
            keywords.append("光晕")
        effects.append({
            "scene_index": i,
            "visual_style": visual or "现代简约",
            "animation_keywords": keywords,
            "generate_image": False,
            "generate_image_prompt": "",
        })
    return {"effects": effects}
