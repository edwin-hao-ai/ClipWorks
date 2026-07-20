"""素材命名与重复落库回归测试（UX 巡检发现的真实 bug）：

1. download_image 此前把所有远程图统一写成 <project>/img.jpg——同一项目多张
   自动配图互相覆盖，素材库里一排「1080」还指向同一个文件。修复后按 URL
   哈希生成确定性唯一文件名。
2. build_soundtrack 每次渲染都新建一条指向同一个 soundtrack.wav 的 MediaAsset
   行，素材库重复堆积。修复后复用已有行。
"""

import os

from app.database import SessionLocal
from app.models import MediaAsset, Project, User
from app.services import assets as assets_svc
from app.services import audio_track


def test_download_image_uses_unique_names_per_url(tmp_path, monkeypatch):
    monkeypatch.setattr(assets_svc, "ASSETS_DIR", str(tmp_path))
    monkeypatch.setattr(assets_svc, "safe_get", lambda *a, **k: (b"fake-image-bytes", None))

    p1 = assets_svc.download_image("https://picsum.photos/seed/a/1920/1080", "proj-1")
    p2 = assets_svc.download_image("https://picsum.photos/seed/b/1920/1080", "proj-1")
    p1_again = assets_svc.download_image("https://picsum.photos/seed/a/1920/1080", "proj-1")

    assert p1 and p2
    assert p1 != p2, "不同 URL 必须落到不同文件，不能再统一覆盖 img.jpg"
    assert p1 == p1_again, "同一 URL 重复下载应保持幂等（覆盖自己）"
    assert os.path.basename(p1).startswith("img_")
    assert os.path.exists(p1) and os.path.exists(p2)


def test_download_image_honors_explicit_asset_id(tmp_path, monkeypatch):
    monkeypatch.setattr(assets_svc, "ASSETS_DIR", str(tmp_path))
    monkeypatch.setattr(assets_svc, "safe_get", lambda *a, **k: (b"x", None))

    p = assets_svc.download_image("https://example.com/a.png", "proj-2", asset_id="hero")
    assert os.path.basename(p) == "hero.png"


def test_build_soundtrack_reuses_asset_row(tmp_path, monkeypatch):
    """同一项目重复渲染：soundtrack.wav 被覆盖，但 MediaAsset 行必须复用。"""
    monkeypatch.setattr(audio_track, "ASSETS_DIR", str(tmp_path))

    class _Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"success": True}

    def _post(url, json=None, timeout=None):
        # 模拟渲染服务真的写出了音轨文件
        with open(json["output_path"], "wb") as f:
            f.write(b"wav-bytes")
        return _Resp()

    monkeypatch.setattr(audio_track.httpx, "post", _post)

    db = SessionLocal()
    try:
        user = User(email="snd-test@example.com", name="t", provider="mock")
        db.add(user)
        db.commit()
        db.refresh(user)
        project = Project(user_id=user.id, title="音轨测试", status="ready")
        db.add(project)
        db.commit()
        db.refresh(project)

        comp = {"duration": 10, "tracks": []}  # 无文本轨 → 无旁白，走 BGM-only
        id1 = audio_track.build_soundtrack(project, comp, db)
        id2 = audio_track.build_soundtrack(project, comp, db)

        assert id1 and id1 == id2, "重复渲染必须复用同一条音轨资产行"
        rows = db.query(MediaAsset).filter(MediaAsset.project_id == project.id).all()
        assert len(rows) == 1
        assert rows[0].type == "audio" and rows[0].source == "generated"
    finally:
        db.close()
