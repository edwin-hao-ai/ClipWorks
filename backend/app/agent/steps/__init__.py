from app.agent.steps.script_step import run as run_script

STEPS = {
    "script": run_script,
}

ORDER = ["script", "assets", "scenes", "effects"]


def run_step(step_name: str, project, state: dict, user_input: str | None = None):
    if step_name not in STEPS:
        raise ValueError(f"Unknown step: {step_name}")
    return STEPS[step_name](project, state, user_input)


def previous_step(step_name: str) -> str | None:
    try:
        idx = ORDER.index(step_name)
    except ValueError:
        return None
    return ORDER[idx - 1] if idx > 0 else None
