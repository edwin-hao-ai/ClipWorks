"""LLM JSON 解析容错单测：宽松解析（围栏/噪声）+ 空响应/解析失败重试一次。"""

from app.agent.llm import KimiClient, _parse_json_lenient


def test_lenient_parse_plain_json():
    assert _parse_json_lenient('{"a": 1}') == {"a": 1}


def test_lenient_parse_strips_code_fence():
    content = '```json\n{"title": "T", "scenes": []}\n```'
    assert _parse_json_lenient(content) == {"title": "T", "scenes": []}


def test_lenient_parse_extracts_embedded_object():
    content = '好的，这是方案：\n{"title": "T"}\n希望对你有帮助'
    assert _parse_json_lenient(content) == {"title": "T"}


def test_lenient_parse_returns_none_on_garbage():
    assert _parse_json_lenient("完全不是 JSON") is None
    assert _parse_json_lenient("") is None


class _FakeClient(KimiClient):
    """跳过真实 OpenAI 初始化，chat_completion 用脚本化返回值。"""

    def __init__(self, contents):
        self._contents = list(contents)
        self.calls = 0
        self._available = True

    def chat_completion(self, **kwargs):
        self.calls += 1
        return self._contents.pop(0) if self._contents else None


def test_json_retry_on_empty_then_success():
    client = _FakeClient(["", '{"ok": true}'])
    assert client.chat_completion_json("s", "u") == {"ok": True}
    assert client.calls == 2


def test_json_retry_on_garbage_then_success():
    client = _FakeClient(["嗯……我想想", '```json\n{"ok": 1}\n```'])
    assert client.chat_completion_json("s", "u") == {"ok": 1}
    assert client.calls == 2


def test_json_gives_up_after_two_attempts():
    client = _FakeClient(["", "还是不行"])
    assert client.chat_completion_json("s", "u") is None
    assert client.calls == 2
