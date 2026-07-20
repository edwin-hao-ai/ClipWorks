import json
import logging
import re
from typing import Optional

from .llm import KimiClient
from .prompts import MODIFY_VIDEO

logger = logging.getLogger(__name__)


UNSUPPORTED_MODIFY_REPLY = (
    "我目前能直接处理：变红、加大字号、缩短/延长、调整画幅（如「改成 9:16」「换成竖屏」）、"
    "添加文字片段（如「添加文字：你好」）、删除最后一个片段。"
    "更复杂的修改请点『重新规划』。"
)

_ADD_TEXT_RE = re.compile(
    r"(?:添加文字|添加字幕|加一句|新增文字|加一段文字)\s*[:：]?\s*(.+)$"
)
_DELETE_LAST_RE = re.compile(r"(删除|删掉|移除).*(最后|最后一个|最后一段|末段|末个)")

# 画幅指令：显式比例或方向关键词。与 render_task._apply_target_format 共用同一套尺寸。
_FORMAT_DIMS = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080)}
_RATIO_RE = re.compile(r"(16\s*:\s*9|9\s*:\s*16|1\s*:\s*1)")
_FORMAT_KEYWORDS = [
    ("竖屏", "9:16"), ("竖版", "9:16"), ("竖向", "9:16"),
    ("横屏", "16:9"), ("横版", "16:9"), ("横向", "16:9"),
    ("方形", "1:1"), ("方屏", "1:1"), ("正方", "1:1"),
]


def _detect_target_format(message: str) -> Optional[str]:
    m = _RATIO_RE.search(message)
    if m:
        return m.group(1).replace(" ", "")
    for keyword, fmt in _FORMAT_KEYWORDS:
        if keyword in message:
            return fmt
    return None


def _rescale_composition(modified: dict, target_format: str) -> None:
    """按轴比例缩放所有 clip 的 position（字号按纵向比例），并更新画布尺寸。"""
    w, h = _FORMAT_DIMS[target_format]
    old_w, old_h = modified.get("width"), modified.get("height")
    if old_w and old_h and (old_w, old_h) != (w, h):
        sx, sy = w / old_w, h / old_h
        for _track, clip in _all_clips(modified):
            pos = clip.get("position")
            if isinstance(pos, dict):
                pos["x"] = round(pos.get("x", 0) * sx)
                pos["width"] = round(pos.get("width", old_w) * sx)
                pos["y"] = round(pos.get("y", 0) * sy)
                pos["height"] = round(pos.get("height", old_h) * sy)
            style = clip.get("style")
            if isinstance(style, dict) and isinstance(style.get("fontSize"), (int, float)):
                style["fontSize"] = max(12, round(style["fontSize"] * sy))
    modified["width"], modified["height"] = w, h


def _gen_clip_id() -> str:
    import uuid
    return f"clip-{uuid.uuid4().hex[:12]}"


def _all_clips(modified: dict):
    for track in modified.get("tracks", []):
        for clip in track.get("clips", []):
            yield track, clip


def _extract_text(message: str) -> Optional[str]:
    m = _ADD_TEXT_RE.search(message)
    if not m:
        return None
    content = m.group(1).strip()
    # strip surrounding quotes/brackets if present
    content = content.strip("「」\"“”'‘’《》").strip()
    return content or None


def _deterministic_modify(
    composition: dict, user_message: str, scene_id: Optional[str] = None
) -> Optional[dict]:
    """Fast, deterministic edits for unambiguous commands.

    Returns a result dict when it applied a change, or None when the message is
    not a recognized simple command (so the caller can fall through to the LLM).
    """
    modified = json.loads(json.dumps(composition))
    message_lower = user_message.lower()
    applied = False
    action = None

    # scene-scoped tweaks (existing behaviour)
    if scene_id:
        for track in modified.get("tracks", []):
            for clip in track.get("clips", []):
                if clip.get("scene_id") == scene_id or clip.get("id") == scene_id:
                    if "红" in user_message or "red" in message_lower:
                        clip.setdefault("style", {})["color"] = "#ef4444"; applied = True; action = "变红"
                    if "大" in user_message or "big" in message_lower:
                        clip.setdefault("style", {})["fontSize"] = 96; applied = True; action = "加大字号"
                    if "短" in user_message or "short" in message_lower:
                        clip["duration"] = max(1, clip.get("duration", 5) - 2); applied = True; action = "缩短"
                    if ("删除" in user_message or "删掉" in user_message or "remove" in message_lower):
                        track["clips"] = [c for c in track["clips"] if c is not clip]
                        applied = True; action = "删除片段"
                    if applied:
                        return _wrap_reply(modified, action or user_message, scene_id=scene_id)
                    return None

    # 画幅调整（如「把画幅改成 9:16」「换成竖屏」）：确定性按轴缩放，
    # 不依赖 LLM；回传 target_format 让路由同步到项目设置。
    target_format = _detect_target_format(user_message)
    if not applied and target_format:
        _rescale_composition(modified, target_format)
        result = _wrap_reply(modified, f"将画幅调整为 {target_format}", scene_id=scene_id)
        result["target_format"] = target_format
        return result

    # add a text clip: 添加文字：xxx / 添加字幕"xxx"
    text_to_add = _extract_text(user_message)
    if text_to_add is not None:
        tracks = modified.setdefault("tracks", [])
        target = next((t for t in tracks if t.get("type") in ("text", "overlay")), None)
        if target is None:
            target = {"id": _gen_clip_id(), "type": "text", "index": max([t.get("index", 0) for t in tracks] or [-1]) + 1,
                      "name": "字幕", "clips": []}
            tracks.append(target)
        last_end = max(
            [c.get("start_time", 0) + c.get("duration", 0) for c in target.get("clips", [])] or [0]
        )
        target.setdefault("clips", []).append({
            "id": _gen_clip_id(), "start_time": round(last_end, 2), "duration": 3,
            "text_content": text_to_add, "style": {}, "position": {},
        })
        applied = True; action = f"添加文字「{text_to_add}」"

    # delete the last clip (across all tracks, by start_time)
    if not applied and _DELETE_LAST_RE.search(user_message):
        last_track = last_clip = None
        last_start = -1.0
        for track, clip in _all_clips(modified):
            if clip.get("start_time", 0) >= last_start:
                last_start = clip.get("start_time", 0); last_track = track; last_clip = clip
        if last_track is not None and last_clip is not None:
            last_track["clips"] = [c for c in last_track["clips"] if c is not last_clip]
            applied = True; action = "删除最后一个片段"

    # global style / duration tweaks (existing behaviour)
    if not applied and ("短" in user_message or "short" in message_lower):
        modified["duration"] = max(5, modified.get("duration", 30) // 2)
        applied = True; action = "整体缩短"
    if "红" in user_message or "red" in message_lower:
        for _track, clip in _all_clips(modified):
            clip.setdefault("style", {})["color"] = "#ef4444"
            applied = True; action = action or "变红"
    if not applied:
        return None
    return _wrap_reply(modified, action or user_message, scene_id=scene_id)


def _unsupported_reply(composition: dict) -> dict:
    # 既未命中确定性指令、LLM 也不可用时：原样返回，并诚实说明能力边界。
    # changed=False 让调用方（agent 路由）不要为「什么都没改」入队渲染、白扣额度。
    return {"reply": UNSUPPORTED_MODIFY_REPLY, "composition": composition, "changed": False}


def _wrap_reply(composition: dict, action: str, scene_id: Optional[str] = None) -> dict:
    reply = f"已针对场景{action}" if scene_id else f"已{action}"
    return {"reply": reply, "composition": composition, "changed": True}


def modify_video(composition: dict, user_message: str, scene_id: Optional[str] = None) -> dict:
    """Modify composition based on natural language instruction.

    Returns a dict with ``reply`` (a human-readable response) and
    ``composition`` (the updated composition dict).

    Unambiguous, common edits (变红/缩短/添加文字/删除最后一段…) are handled by
    a deterministic fast-path so the chat feels instant and stays consistent
    even when the LLM is slow; only unrecognized/complex requests reach the
    LLM, and an honest reply is returned when neither can handle it.
    """
    quick = _deterministic_modify(composition, user_message, scene_id)
    if quick is not None:
        return quick

    prompt = json.dumps({
        "composition": composition,
        "user_message": user_message,
        "scene_id": scene_id,
    }, ensure_ascii=False, indent=2)

    try:
        client = KimiClient()
        result = client.chat_completion_json(
            system_prompt=MODIFY_VIDEO,
            user_prompt=prompt,
        )
        if result and isinstance(result, dict):
            reply = result.get("reply", "")
            if "composition" in result:
                logger.info("Composition modified via LLM")
                return {"reply": reply, "composition": result["composition"], "changed": True}
            if "tracks" in result:
                logger.info("Composition modified via LLM")
                return {"reply": reply, "composition": result, "changed": True}
    except Exception as exc:
        logger.error("modify_video LLM failed, no deterministic handler: %s", exc)

    return _unsupported_reply(composition)
