"""Verify editor drag-to-move and edge-trim persist after save.

Run: .e2e-venv/bin/python scripts/e2e_drag.py
"""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
API = "http://localhost:8000"
OUT = Path("/Users/edwinhao/ClipWorks/data/e2e_audit")
PPS = 24  # default zoom (Timeline ZOOM_LEVELS[1])


def main():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        ctx.request.post(f"{API}/auth/mock-login?provider=google")
        page = ctx.new_page(); page.set_default_timeout(20000)
        fresh = ctx.request.post(f"{API}/projects/", headers={"Content-Type": "application/json"},
                                 data=json.dumps({"title": "e2e-drag", "source_url": "", "source_type": "url"}))
        pid = fresh.json()["id"]

        page.goto(f"{BASE}/projects/{pid}/editor", wait_until="domcontentloaded")
        try: page.wait_for_load_state("networkidle", timeout=10000)
        except Exception: pass
        page.wait_for_timeout(1500)

        comp = ctx.request.get(f"{API}/compositions/{pid}").json()
        # pick a labeled clip to track across save (ids regenerate on PUT)
        labeled = None
        for t in comp["tracks"]:
            for c in t["clips"]:
                if c.get("text_content") == "ClipWorks":
                    labeled = c; break
            if labeled: break
        assert labeled, "need a ClipWorks clip"
        before_start, before_dur = labeled["start_time"], labeled["duration"]

        clip = page.locator("div.absolute.top-1\\.5").first
        box = clip.bounding_box()
        cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2

        # 1) drag body to the right by ~120px -> start_time += 120/PPS
        page.mouse.move(cx, cy); page.mouse.down()
        for i in range(1, 11):
            page.mouse.move(cx + 12 * i, cy); page.wait_for_timeout(20)
        page.mouse.up(); page.wait_for_timeout(300)

        # 2) drag RIGHT trim handle right by ~48px -> duration += 48/PPS
        box2 = clip.bounding_box()
        rx, ry = box2["x"] + box2["width"] - 2, box2["y"] + box2["height"] / 2
        page.mouse.move(rx, ry); page.mouse.down()
        for i in range(1, 9):
            page.mouse.move(rx + 6 * i, ry); page.wait_for_timeout(20)
        page.mouse.up(); page.wait_for_timeout(300)

        page.get_by_role("button", name="保存").click(); page.wait_for_timeout(1800)
        after = ctx.request.get(f"{API}/compositions/{pid}").json()
        moved = None
        for t in after["tracks"]:
            for c in t["clips"]:
                if c.get("text_content") == "ClipWorks":
                    moved = c; break
            if moved: break
        page.screenshot(path=str(OUT / "drag_editor.png"), full_page=True)

        exp_start = round(before_start + 120 / PPS, 1)
        exp_dur = round(before_dur + 48 / PPS, 1)
        ok_start = moved and abs(moved["start_time"] - exp_start) <= 0.2
        ok_dur = moved and abs(moved["duration"] - exp_dur) <= 0.25
        print("before", before_start, before_dur, "after", moved["start_time"], moved["duration"],
              "want~", exp_start, exp_dur)
        print("DRAG_MOVE", "PASS" if ok_start else "FAIL")
        print("TRIM_RIGHT", "PASS" if ok_dur else "FAIL")
        b.close()


if __name__ == "__main__":
    main()
