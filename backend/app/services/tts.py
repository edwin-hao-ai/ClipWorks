"""可插拔 TTS（旁白）提供者。

设计原则：real-when-available + 确定性兜底。提供者按优先级链选择：
1. 配置了 OPENAI_API_KEY（或兼容的 TTS_API_KEY）时，调用真实在线 TTS 生成旁白；
2. 无密钥时尝试 edge-tts（微软在线语音，免密钥、音质接近商用，需网络）；
3. edge-tts 不可用/失败时退到本地 espeak-ng（机械音，但 100% 离线、确定性）；
4. 全部不可用时 synthesize_narration 返回 False，调用方退到 BGM-only 兜底，
   保证最终成片仍然有可混入的音轨，而绝不因外部依赖缺失而崩溃。

synthesize_narration 逐段遍历整条链：首选提供者网络抖动时不会让旁白整段消失，
而是自动落到下一个可用提供者。新增真实提供者只需实现 TTSProvider 并加入链路。
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
from typing import Optional, Protocol

logger = logging.getLogger(__name__)


class TTSProvider(Protocol):
    name: str

    def synthesize(self, text: str, out_path: str) -> bool:
        """Synthesize `text` into `out_path` (wav). Return True on success."""
        ...


class OpenAITTS:
    """OpenAI 兼容 TTS（tts-1 / tts-1-hd）。需 OPENAI_API_KEY。"""

    name = "openai"

    def __init__(self) -> None:
        self.api_key = os.getenv("TTS_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("TTS_BASE_URL") or os.getenv("OPENAI_BASE_URL")
        self.model = os.getenv("TTS_MODEL", "tts-1")
        self.voice = os.getenv("TTS_VOICE", "alloy")

    def synthesize(self, text: str, out_path: str) -> bool:
        if not self.api_key or not text.strip():
            return False
        try:
            from openai import OpenAI  # 延迟导入：无密钥时连依赖都不必装

            client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
            # 优先请求 wav，便于浏览器与 ffmpeg 直接处理；不支持时退到 mp3。
            fmt = "wav" if out_path.lower().endswith(".wav") else "mp3"
            try:
                resp = client.audio.speech.create(
                    model=self.model, voice=self.voice, input=text, response_format=fmt
                )
            except Exception:
                resp = client.audio.speech.create(
                    model=self.model, voice=self.voice, input=text
                )
            content = getattr(resp, "content", None)
            if content is None:
                # openai>=1.0: response 支持 .read()
                content = resp.read()
            with open(out_path, "wb") as f:
                f.write(content)
            return os.path.exists(out_path) and os.path.getsize(out_path) > 0
        except Exception as exc:  # noqa: BLE001 - 任何失败都降级
            logger.warning("TTS synthesize failed (%s): %s", self.name, exc)
            return False


class EspeakTTS:
    """espeak-ng 本地合成：无 API 密钥时的确定性可听兜底。

    音质是机械音，但完全离线、零成本、确定性——保证「无 key 环境也一定有可听旁白」。
    默认中文声 cmn（可用 ESPEAK_VOICE 覆盖）；镜像未装 espeak-ng 时 available=False，
    链路上自动跳过本提供者。
    """

    name = "espeak"

    def __init__(self) -> None:
        self.binary = shutil.which("espeak-ng") or shutil.which("espeak")
        self.voice = os.getenv("ESPEAK_VOICE", "cmn")
        self.rate = os.getenv("ESPEAK_RATE", "150")  # 词/分钟，略慢更稳

    @property
    def available(self) -> bool:
        return bool(self.binary)

    def synthesize(self, text: str, out_path: str) -> bool:
        if not self.binary or not text.strip():
            return False
        try:
            os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
            subprocess.run(
                [
                    self.binary,
                    "-v",
                    self.voice,
                    "-s",
                    self.rate,
                    "-w",
                    out_path,
                    "--",
                    text,
                ],
                check=True,
                capture_output=True,
                timeout=60,
            )
            return os.path.exists(out_path) and os.path.getsize(out_path) > 0
        except Exception as exc:  # noqa: BLE001 - 任何失败都降级
            logger.warning("TTS synthesize failed (%s): %s", self.name, exc)
            return False


class EdgeTTS:
    """edge-tts（微软在线语音）：免密钥、音质接近商用的中间层。

    需要网络与 edge-tts 包；任一缺失 available=False 自动跳过。
    输出为 mp3（与扩展名无关，下游 ffmpeg 按内容探测，混音不受影响）。
    运行期网络失败时 synthesize 返回 False，链路自动落到 espeak。
    """

    name = "edge"

    def __init__(self) -> None:
        self.voice = os.getenv("EDGE_TTS_VOICE", "zh-CN-XiaoxiaoNeural")
        self.rate = os.getenv("EDGE_TTS_RATE", "+0%")

    @property
    def available(self) -> bool:
        try:
            import edge_tts  # noqa: F401

            return True
        except ImportError:
            return False

    def synthesize(self, text: str, out_path: str) -> bool:
        if not self.available or not text.strip():
            return False
        try:
            import asyncio

            import edge_tts

            os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

            async def _run() -> None:
                communicate = edge_tts.Communicate(text, self.voice, rate=self.rate)
                await communicate.save(out_path)

            asyncio.run(_run())
            return os.path.exists(out_path) and os.path.getsize(out_path) > 1000
        except Exception as exc:  # noqa: BLE001 - 任何失败都降级到下一个提供者
            logger.warning("TTS synthesize failed (%s): %s", self.name, exc)
            return False


_provider: Optional[TTSProvider] = None


def _provider_chain() -> list:
    """按优先级构建可用提供者链：OpenAI 兼容接口 -> edge-tts -> espeak-ng。"""
    chain: list = []
    candidate = OpenAITTS()
    if candidate.api_key:
        chain.append(candidate)
    edge = EdgeTTS()
    if edge.available:
        chain.append(edge)
    espeak = EspeakTTS()
    if espeak.available:
        chain.append(espeak)
    return chain


def get_tts_provider() -> Optional[TTSProvider]:
    """返回链路首选提供者（用于日志/兼容）；逐段合成请用 synthesize_narration。"""
    global _provider
    if _provider is None:
        chain = _provider_chain()
        _provider = chain[0] if chain else None
    return _provider


def synthesize_narration(text: str, out_path: str) -> bool:
    """按优先级链逐段合成旁白：首选提供者失败自动落到下一个，全部失败返回 False。"""
    for provider in _provider_chain():
        if provider.synthesize(text, out_path):
            return True
    return False
