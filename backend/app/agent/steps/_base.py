import json
import re
from typing import Optional


def extract_json_block(text: str) -> Optional[str]:
    if "```json" in text:
        return text.split("```json")[1].split("```")[0].strip()
    if "```" in text:
        return text.split("```")[1].split("```")[0].strip()
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
