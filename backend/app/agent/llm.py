import json
import logging
import re
from typing import Optional

from openai import OpenAI

from app.config import KIMI_API_KEY, KIMI_BASE_URL, KIMI_MODEL

logger = logging.getLogger(__name__)


def _parse_json_lenient(content: str):
    """尽力从 LLM 响应里解析 JSON：直解析 -> 去代码围栏 -> 截取最外层 {} 或 []。

    LLM 偶尔会在 JSON 外面包 ```json 围栏或前后附解释文字，直接 json.loads
    会整单失败、全链路退到兜底方案；这里先把这些常见噪声洗掉。
    """
    text = content.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text.strip())
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    for opener, closer in (("{", "}"), ("[", "]")):
        start = text.find(opener)
        end = text.rfind(closer)
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                continue
    return None


class LLMUnavailableError(Exception):
    """Raised when the Kimi LLM cannot be reached (missing key or API failure).

    Callers can catch this to degrade gracefully (e.g. emit a deterministic
    fallback plan) instead of surfacing a generic error to the user.
    """


class KimiClient:
    def __init__(self, model: Optional[str] = None, timeout: float = 120, max_retries: int = 1):
        self.model = model or KIMI_MODEL
        # 缺少 KIMI_API_KEY（或凭据无效）时不要崩溃；标记为不可用，
        # 让调用方走确定性降级分支，而不是向用户抛出通用错误。
        self._available = bool(KIMI_API_KEY)
        self.client = None
        if self._available:
            try:
                self.client = OpenAI(
                    base_url=KIMI_BASE_URL,
                    api_key=KIMI_API_KEY,
                    timeout=timeout,
                    max_retries=max_retries,
                )
            except Exception as exc:
                logger.warning("Kimi client init failed, running in fallback mode: %s", exc)
                self._available = False
                self.client = None

    def chat_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        json_mode: bool = False,
        temperature: float = 1.0,
        max_retries: int = 1,
    ) -> Optional[str]:
        if not self._available or self.client is None:
            raise LLMUnavailableError("KIMI_API_KEY is not set")
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

    def chat_completion_stream(
        self,
        system_prompt: str,
        messages: list[dict],
        temperature: float = 1.0,
    ):
        """Yield content chunks from a streaming chat completion.

        Raises ``LLMUnavailableError`` when the API key is missing or the
        request fails, so callers can fall back instead of streaming a
        generic error to the user. The successful streaming path is unchanged.
        """
        if not self._available or self.client is None:
            raise LLMUnavailableError("KIMI_API_KEY is not set")
        all_messages = [{"role": "system", "content": system_prompt}, *messages]
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=all_messages,
                temperature=temperature,
                stream=True,
            )
            for chunk in response:
                delta = chunk.choices[0].delta.content
                if delta:
                    yield delta
        except LLMUnavailableError:
            raise
        except Exception as exc:
            logger.warning("Kimi streaming API call failed: %s", exc)
            raise LLMUnavailableError(str(exc)) from exc

    def chat_completion_json(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 1.0,
        max_retries: int = 1,
    ) -> Optional[dict]:
        # 解析失败/空响应重试一次：LLM 偶发返回空串或非 JSON 噪声，直接退兜底
        # 会浪费一次成功的 API 调用；重试一次可把这类抖动消化掉大半。
        for attempt in range(2):
            content = self.chat_completion(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                json_mode=True,
                temperature=temperature,
                max_retries=max_retries if attempt == 0 else 0,
            )
            if not content:
                logger.warning("Kimi returned empty content (attempt %d/2)", attempt + 1)
                continue
            parsed = _parse_json_lenient(content)
            if parsed is not None:
                return parsed
            logger.warning(
                "Failed to parse Kimi JSON response (attempt %d/2): %.200s",
                attempt + 1,
                content,
            )
        logger.error("Kimi JSON response unparsable after 2 attempts; caller will fall back")
        return None


def chat_completion(system_prompt: str, user_prompt: str, json_mode: bool = False) -> Optional[str]:
    """Convenience wrapper that does not require instantiating KimiClient."""
    client = KimiClient()
    return client.chat_completion(system_prompt, user_prompt, json_mode=json_mode)
