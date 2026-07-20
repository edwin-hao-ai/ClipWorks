from app.agent.conversation import build_fallback_plan


def fallback_script(project, state):
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
