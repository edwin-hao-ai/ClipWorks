import os
from unittest.mock import MagicMock, patch

import pytest

from app.services.media_proxy import ensure_proxy


def test_ensure_proxy_returns_original_webm(tmp_path):
    webm = tmp_path / "clip.webm"
    webm.write_text("fake webm")
    assert ensure_proxy("video", str(webm)) == str(webm)


def test_ensure_proxy_returns_original_wav(tmp_path):
    wav = tmp_path / "audio.wav"
    wav.write_text("fake wav")
    assert ensure_proxy("audio", str(wav)) == str(wav)


def test_ensure_proxy_calls_renderer_for_video(tmp_path):
    mp4 = tmp_path / "clip.mp4"
    mp4.write_text("fake mp4")
    proxy = tmp_path / "clip.remotion.webm"
    proxy.write_text("fake webm")

    mock_response = MagicMock()
    mock_response.json.return_value = {"success": True, "output_path": str(proxy)}
    mock_response.raise_for_status.return_value = None

    metadata = {}
    with patch("app.services.media_proxy.httpx.post", return_value=mock_response) as mock_post:
        result = ensure_proxy("video", str(mp4), metadata)

    assert result == str(proxy)
    assert metadata["proxy_path"] == str(proxy)
    mock_post.assert_called_once()
    call_args = mock_post.call_args.kwargs["json"]
    assert call_args["input_path"] == str(mp4)
    assert call_args["output_path"] == str(proxy)
    assert call_args["asset_type"] == "video"


def test_ensure_proxy_calls_renderer_for_audio(tmp_path):
    mp3 = tmp_path / "audio.mp3"
    mp3.write_text("fake mp3")
    proxy = tmp_path / "audio.remotion.ogg"
    proxy.write_text("fake ogg")

    mock_response = MagicMock()
    mock_response.json.return_value = {"success": True, "output_path": str(proxy)}
    mock_response.raise_for_status.return_value = None

    metadata = {}
    with patch("app.services.media_proxy.httpx.post", return_value=mock_response) as mock_post:
        result = ensure_proxy("audio", str(mp3), metadata)

    assert result == str(proxy)
    assert metadata["proxy_path"] == str(proxy)
    call_args = mock_post.call_args.kwargs["json"]
    assert call_args["asset_type"] == "audio"


def test_ensure_proxy_raises_for_missing_file(tmp_path):
    missing = tmp_path / "missing.mp4"
    with pytest.raises(FileNotFoundError):
        ensure_proxy("video", str(missing))


def test_ensure_proxy_raises_when_renderer_fails(tmp_path):
    mp4 = tmp_path / "clip.mp4"
    mp4.write_text("fake mp4")

    mock_response = MagicMock()
    mock_response.json.return_value = {"success": False, "error": "codec not supported"}
    mock_response.raise_for_status.return_value = None

    with patch("app.services.media_proxy.httpx.post", return_value=mock_response):
        with pytest.raises(RuntimeError, match="codec not supported"):
            ensure_proxy("video", str(mp4))
