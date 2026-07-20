import json
import re
from typing import Optional


def extract_json_block(text: str) -> Optional[str]:
    # Prefer an explicit ```json fence so multiple fenced blocks do not confuse us.
    match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def parse_json(text: str) -> Optional[dict]:
    try:
        return json.loads(extract_json_block(text))
    except Exception:
        return None


def sse_token(text: str) -> str:
    return json.dumps({"type": "token", "text": text}, ensure_ascii=False)


def sse_done() -> str:
    return json.dumps({"type": "done"}, ensure_ascii=False)


def sse_error(message: str) -> str:
    return json.dumps({"type": "error", "message": message}, ensure_ascii=False)
