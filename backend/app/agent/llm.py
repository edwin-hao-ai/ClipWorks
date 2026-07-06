import json
import logging
from typing import Optional

from openai import OpenAI

from app.config import KIMI_API_KEY, KIMI_BASE_URL, KIMI_MODEL

logger = logging.getLogger(__name__)


class KimiClient:
    def __init__(self):
        self.client = OpenAI(
            base_url=KIMI_BASE_URL,
            api_key=KIMI_API_KEY,
            timeout=120,
            max_retries=1,
        )
        self.model = KIMI_MODEL

    def chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
        temperature: float = 1.0,
        max_retries: int = 1,
    ) -> Optional[str]:
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        for attempt in range(max_retries + 1):
            try:
                response = self.client.chat.completions.create(**kwargs)
                return response.choices[0].message.content
            except Exception as exc:
                logger.warning("Kimi API call failed (attempt %d/%d): %s", attempt + 1, max_retries + 1, exc)
                if attempt == max_retries:
                    raise
        return None

    def chat_completion_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 1.0,
    ) -> Optional[dict]:
        content = self.chat_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            json_mode=True,
            temperature=temperature,
        )
        if not content:
            return None
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse Kimi JSON response: %s", exc)
            return None


def chat_completion(system_prompt: str, user_prompt: str, json_mode: bool = False) -> Optional[str]:
    """Convenience wrapper that does not require instantiating KimiClient."""
    client = KimiClient()
    return client.chat_completion(system_prompt, user_prompt, json_mode=json_mode)
