"""素材绑定测试：把图片 id 回填到缺失 asset_id 的 visual clip。"""

from app.agent.asset_bind import bind_images_to_composition, bind_videos_to_composition


def _comp(tracks):
    return {"width": 1080, "height": 1920, "duration": 15, "tracks": tracks}


def test_binds_images_to_visual_clips_round_robin():
    comp = _comp([
        {"type": "video", "index": 0, "clips": [
            {"start_time": 0, "duration": 3},
            {"start_time": 3, "duration": 3},
            {"start_time": 6, "duration": 3},
        ]},
        {"type": "text", "index": 1, "clips": [{"start_time": 0, "duration": 3, "text_content": "hi"}]},
    ])
    bind_images_to_composition(comp, ["imgA", "imgB"])
    ids = [c.get("asset_id") for c in comp["tracks"][0]["clips"]]
    assert ids == ["imgA", "imgB", "imgA"]  # round-robin
    # 绑定图片后 video 轨道被矫正为 image，确保 Remotion 用 <Img> 渲染
    assert comp["tracks"][0]["type"] == "image"
    # text 轨道不受影响
    assert comp["tracks"][1]["clips"][0].get("asset_id") is None


def test_does_not_override_existing_asset_id():
    comp = _comp([
        {"type": "image", "index": 0, "clips": [
            {"start_time": 0, "duration": 3, "asset_id": "keep-me"},
            {"start_time": 3, "duration": 3},
        ]},
    ])
    bind_images_to_composition(comp, ["imgX"])
    clips = comp["tracks"][0]["clips"]
    assert clips[0]["asset_id"] == "keep-me"
    assert clips[1]["asset_id"] == "imgX"


def test_noop_when_no_images():
    comp = _comp([
        {"type": "video", "index": 0, "clips": [{"start_time": 0, "duration": 3}]},
    ])
    bind_images_to_composition(comp, [])
    assert comp["tracks"][0]["clips"][0].get("asset_id") is None


def test_ignores_text_and_overlay_tracks():
    comp = _comp([
        {"type": "text", "index": 0, "clips": [{"start_time": 0, "duration": 3}]},
        {"type": "overlay", "index": 1, "clips": [{"start_time": 0, "duration": 3}]},
    ])
    bind_images_to_composition(comp, ["imgA"])
    assert comp["tracks"][0]["clips"][0].get("asset_id") is None
    assert comp["tracks"][1]["clips"][0].get("asset_id") is None


def test_flips_video_track_to_image_even_when_clips_already_bound():
    # 场景：clip 的 asset_id 在前一次渲染已写入 DB，本次 comp_json 重建时已带 asset_id，
    # 绑定循环会全部 continue，但轨道仍必须被矫正为 image，否则 Remotion 用 <Video> 加载 png。
    comp = _comp([
        {"type": "video", "index": 0, "clips": [
            {"start_time": 0, "duration": 3, "asset_id": "imgA"},
            {"start_time": 3, "duration": 3, "asset_id": "imgB"},
        ]},
    ])
    bind_images_to_composition(comp, ["imgA", "imgB"])
    assert comp["tracks"][0]["type"] == "image"
    # asset_id 保持不变
    assert [c["asset_id"] for c in comp["tracks"][0]["clips"]] == ["imgA", "imgB"]


def test_binds_videos_to_video_track_round_robin():
    """上传视频绑定：video 轨 clip 按顺序拿到素材 id，轨道类型保持 video。"""
    comp = _comp([
        {"type": "video", "index": 0, "clips": [
            {"start_time": 0, "duration": 3},
            {"start_time": 3, "duration": 3},
            {"start_time": 6, "duration": 3},
        ]},
        {"type": "text", "index": 1, "clips": [{"start_time": 0, "duration": 3, "text_content": "hi"}]},
    ])
    bind_videos_to_composition(comp, ["vidA"])
    clips = comp["tracks"][0]["clips"]
    assert [c["asset_id"] for c in clips] == ["vidA", "vidA", "vidA"]
    assert comp["tracks"][0]["type"] == "video", "绑了真实视频的轨道必须保持 video"
    assert comp["tracks"][1]["clips"][0].get("asset_id") is None


def test_video_binding_runs_before_image_binding():
    """流水线顺序保证：视频先绑，图片不再抢占 video 轨、也不把它矫正成 image。"""
    comp = _comp([
        {"type": "video", "index": 0, "clips": [
            {"start_time": 0, "duration": 3},
            {"start_time": 3, "duration": 3},
        ]},
    ])
    bind_videos_to_composition(comp, ["vidA"])
    bind_images_to_composition(comp, ["imgX"])
    assert [c["asset_id"] for c in comp["tracks"][0]["clips"]] == ["vidA", "vidA"]
    assert comp["tracks"][0]["type"] == "video"


def test_video_binding_noop_without_assets_or_with_existing_ids():
    comp = _comp([
        {"type": "video", "index": 0, "clips": [
            {"start_time": 0, "duration": 3, "asset_id": "keep"},
            {"start_time": 3, "duration": 3},
        ]},
    ])
    bind_videos_to_composition(comp, [])
    assert comp["tracks"][0]["clips"][1].get("asset_id") is None
    bind_videos_to_composition(comp, ["vidA"])
    assert comp["tracks"][0]["clips"][0]["asset_id"] == "keep"
    assert comp["tracks"][0]["clips"][1]["asset_id"] == "vidA"
