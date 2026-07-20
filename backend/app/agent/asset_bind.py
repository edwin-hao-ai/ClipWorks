"""把素材绑定到时间线片段。

商用成片的核心是「真实素材进画面」。当前 pipeline 即使抓到了网页/上传图片，
visual clip 上也没有 asset_id，导致 Remotion/HyperFrames 只能画渐变块。

本模块提供两个纯函数：
- bind_images_to_composition：把已落库的图片素材 id 按场景顺序回填到缺失
  asset_id 的 visual clip（type 为 video/image）上，round-robin 复用，不覆盖
  AI 已经指定的 asset_id；
- bind_videos_to_composition：把上传的视频素材 id 回填到 video 轨 clip 上——
  「上传素材→AI 剪辑」链路的关键一环，缺了它 video-use 引擎收不到任何指向
  真实视频的 clip，上传的视频永远不会出现在成片中。
纯函数、无副作用，便于单测。
"""

from __future__ import annotations

import logging
from typing import Iterable

logger = logging.getLogger(__name__)

_VISUAL_TRACK_TYPES = {"video", "image"}


def bind_images_to_composition(comp_json: dict, image_asset_ids: Iterable[str]) -> dict:
    """把图片素材 id 绑定到缺失 asset_id 的 visual clip 上（原地修改并返回 comp_json）。

    - 仅处理 type 为 video/image 的轨道片段；
    - 已有 asset_id 的片段保持不动（尊重 AI 的选择）；
    - image_asset_ids 为空时直接返回（保持原有渐变兜底行为）；
    - 多于素材时 round-robin 复用，保证每个场景都有图；
    - 关键：当把图片绑定到 type="video" 轨道的片段时，把该轨道类型改为 "image"，
      这样 Remotion 会用 <Img> 而非 <Video> 渲染（<Video> 加载 .png 会解码失败→黑屏）。
      AI 常把图片放在 video 轨道上，这是「渐变块」的另一处根因。
    """
    ids = [i for i in (image_asset_ids or []) if i]
    if not ids:
        return comp_json

    cursor = 0
    bound = 0
    for track in comp_json.get("tracks", []) or []:
        if track.get("type") not in _VISUAL_TRACK_TYPES:
            continue
        track_touched_image = False
        for clip in track.get("clips", []) or []:
            if clip.get("asset_id"):
                if track.get("type") == "image":
                    track_touched_image = True
                continue
            clip["asset_id"] = ids[cursor % len(ids)]
            cursor += 1
            bound += 1
            track_touched_image = True
        # 整条轨道的素材都是图片时，把轨道类型矫正为 image，确保按 <Img> 渲染。
        if track_touched_image and track.get("type") == "video":
            track["type"] = "image"

    # 兜底再扫一遍：素材可能在前一次渲染就已经绑进 DB（clip.asset_id 已存在），
    # 这时上面的循环会 continue、track_touched_image 为 False，导致 video 轨道永远
    # 翻不成 image。这里无条件把「含图片素材 clip」的 video 轨道统一矫正为 image。
    id_set = set(ids)
    for track in comp_json.get("tracks", []) or []:
        if track.get("type") != "video":
            continue
        if any((c.get("asset_id") in id_set) for c in (track.get("clips", []) or [])):
            track["type"] = "image"

    if bound:
        logger.info("bind_images_to_composition: bound %d visual clip(s) to %d asset(s)", bound, len(ids))
    return comp_json


def bind_videos_to_composition(comp_json: dict, video_asset_ids: Iterable[str]) -> dict:
    """把上传的视频素材 id 绑定到 video 轨缺失 asset_id 的 clip 上（原地修改并返回）。

    - 仅处理 type 为 "video" 的轨道（图片/文本/音频/overlay 轨一律不动）；
    - 已有 asset_id 的片段保持不动（尊重 AI 的选择）；
    - 素材少于片段时 round-robin 复用：单条上传视频 + 多个顺序场景 = 按时间线
      顺序切片（video-use 引擎以 clip.start_time 作为源素材 trim 起点，顺序场景
      正好顺序播放源视频的同名区间）；
    - 不做轨道类型矫正——与图片绑定相反，绑了真实视频的轨道必须保持 video，
      video-use 引擎只认 video 轨。
    必须在 bind_images_to_composition 之前调用：否则图片绑定会抢先占据 video 轨
    的 clip 并把轨道矫正成 image，上传的视频就永远进不了画面。
    """
    ids = [i for i in (video_asset_ids or []) if i]
    if not ids:
        return comp_json

    cursor = 0
    bound = 0
    for track in comp_json.get("tracks", []) or []:
        if track.get("type") != "video":
            continue
        for clip in track.get("clips", []) or []:
            if clip.get("asset_id"):
                continue
            clip["asset_id"] = ids[cursor % len(ids)]
            cursor += 1
            bound += 1

    if bound:
        logger.info("bind_videos_to_composition: bound %d video clip(s) to %d asset(s)", bound, len(ids))
    return comp_json
