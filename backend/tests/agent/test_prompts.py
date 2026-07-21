from app.agent.prompts import ARCHITECT_SYSTEM_PROMPT


def test_architect_prompt_exists():
    assert "action" in ARCHITECT_SYSTEM_PROMPT
    assert "ask" in ARCHITECT_SYSTEM_PROMPT
    assert "advance" in ARCHITECT_SYSTEM_PROMPT
