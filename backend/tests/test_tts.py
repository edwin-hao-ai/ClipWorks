"""TTS 提供者链单测：real-when-available + 确定性兜底。

不触 DB、不访问网络；真实 espeak 合成测试在本机/容器有二进制时跑，否则 skip。
"""
import shutil

import pytest

from app.services import tts


@pytest.fixture(autouse=True)
def _reset_provider(monkeypatch):
    # 每个测试都清掉模块级缓存与密钥环境，保证链路选择从零开始。
    # 默认禁用 edge-tts（需要网络/包），需要时单独开启。
    monkeypatch.setattr(tts, "_provider", None)
    monkeypatch.setattr(tts.EdgeTTS, "available", False)
    monkeypatch.delenv("TTS_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("TTS_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)


def test_no_key_no_binary_returns_none(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    assert tts.get_tts_provider() is None
    assert tts.synthesize_narration("你好世界", "/tmp/never_written.wav") is False


def test_no_key_with_espeak_uses_espeak(monkeypatch):
    monkeypatch.setattr(
        shutil, "which", lambda name: "/usr/bin/espeak-ng" if name == "espeak-ng" else None
    )
    provider = tts.get_tts_provider()
    assert provider is not None
    assert provider.name == "espeak"


def test_key_prefers_openai_over_espeak(monkeypatch):
    monkeypatch.setenv("TTS_API_KEY", "sk-test")
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/espeak-ng")
    provider = tts.get_tts_provider()
    assert provider is not None
    assert provider.name == "openai"


def test_edge_sits_between_openai_and_espeak(monkeypatch):
    monkeypatch.setattr(tts.EdgeTTS, "available", True)
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/espeak-ng")
    # 无密钥时首选 edge-tts
    assert tts.get_tts_provider().name == "edge"
    # 有密钥时 OpenAI 仍然最高优先
    monkeypatch.setattr(tts, "_provider", None)
    monkeypatch.setenv("TTS_API_KEY", "sk-test")
    assert tts.get_tts_provider().name == "openai"


def test_synthesize_falls_through_chain_on_failure(monkeypatch, tmp_path):
    """首选提供者合成失败时，必须自动落到下一个可用提供者。"""
    monkeypatch.setattr(tts.EdgeTTS, "available", True)
    monkeypatch.setattr(tts.EdgeTTS, "synthesize", lambda self, text, out: False)

    class _FakeEspeak:
        name = "espeak"

        @property
        def available(self):
            return True

        def synthesize(self, text, out_path):
            with open(out_path, "wb") as f:
                f.write(b"RIFF-fake-espeak")
            return True

    monkeypatch.setattr(tts, "EspeakTTS", _FakeEspeak)
    out = tmp_path / "seg.wav"
    assert tts.synthesize_narration("你好", str(out)) is True
    assert out.read_bytes() == b"RIFF-fake-espeak"


def test_edge_unavailable_when_package_missing(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def _no_edge(name, *a, **k):
        if name == "edge_tts":
            raise ImportError("no edge_tts")
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", _no_edge)
    assert tts.EdgeTTS().available is False


def test_espeak_unavailable_synthesize_false(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda name: None)
    provider = tts.EspeakTTS()
    assert provider.available is False
    assert provider.synthesize("你好", "/tmp/never_written2.wav") is False


def test_espeak_real_synthesis(tmp_path):
    """镜像里装了 espeak-ng 时真合成一条中文旁白，校验 wav 非空。"""
    if not (shutil.which("espeak-ng") or shutil.which("espeak")):
        pytest.skip("espeak-ng not installed in this environment")
    out = tmp_path / "seg.wav"
    ok = tts.EspeakTTS().synthesize("世界再吵，一键静下来", str(out))
    assert ok
    assert out.stat().st_size > 1000
