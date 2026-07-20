"""Verify editor same-track collision prevention and single-step drag undo.

A same-track overlap created by dragging must be resolved on commit (and
persisted), and a single undo must fully restore the pre-drag position
(proving the drag produced exactly one history entry, not one per pointermove).

Run: .e2e-venv/bin/python scripts/e2e_overlap.py
"""
import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
API = "http://localhost:8000"
OUT = Path("/Users/edwinhao/ClipWorks/data/e2e_audit")
PPS = 24  # default zoom (Timeline ZOOM_LEVELS[1])


def main():
    ok = True
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        ctx.request.post(f"{API}/auth/mock-login?provider=google")
        page = ctx.new_page(); page.set_default_timeout(20000)

        fresh = ctx.request.post(
            f"{API}/projects/",
            headers={"Content-Type": "application/json"},
            data=json.dumps({"title": "e2e-overlap", "source_url": "", "source_type": "url"}),
        )
        pid = fresh.json()["id"]

        # deterministic two-clip, single-track layout: A@0/5 (ends 5), B@6/3 (6..9)
        ctx.request.put(
            f"{API}/compositions/{pid}",
            headers={"Content-Type": "application/json"},
            data=json.dumps({
                "tracks": [{
                    "type": "video", "index": 0, "name": "video",
                    "clips": [
                        {"start_time": 0, "duration": 5, "text_content": "OverlapA"},
                        {"start_time": 6, "duration": 3, "text_content": "OverlapB"},
                    ],
                }],
            }),
        )

        def comp():
            return ctx.request.get(f"{API}/compositions/{pid}").json()

        def video_clips():
            for t in comp()["tracks"]:
                if t["type"] == "video":
                    return sorted(t["clips"], key=lambda c: c["start_time"])
            return []

        def save():
            page.get_by_role("button", name="保存").click(); page.wait_for_timeout(1600)

        page.goto(f"{BASE}/projects/{pid}/editor", wait_until="domcontentloaded")
        try: page.wait_for_load_state("networkidle", timeout=10000)
        except Exception: pass
        page.wait_for_timeout(1500)

        a = page.locator("div.absolute.top-1\\.5", has_text="OverlapA").first
        box = a.bounding_box()
        assert box, "OverlapA clip block not found"
        cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2

        # drag A right by 168px = 7s @24pps -> A.start lands inside B (6..9) => overlap
        dx_total = 168
        page.mouse.move(cx, cy); page.mouse.down()
        steps = 12
        for i in range(1, steps + 1):
            page.mouse.move(cx + dx_total * i / steps, cy); page.wait_for_timeout(20)
        page.mouse.up(); page.wait_for_timeout(400)

        save()
        after = video_clips()
        page.screenshot(path=str(OUT / "overlap_editor.png"), full_page=True)

        non_overlap = all(
            after[i]["start_time"] >= after[i - 1]["start_time"] + after[i - 1]["duration"] - 0.05
            for i in range(1, len(after))
        )
        a_after = next(c for c in after if c.get("text_content") == "OverlapA")
        print("after drag:", [(c["text_content"], c["start_time"], c["duration"]) for c in after])
        print("NON_OVERLAP", "PASS" if (len(after) == 2 and non_overlap) else "FAIL",
              f"sorted={[(c['start_time'], c['duration']) for c in after]}")
        ok = ok and len(after) == 2 and non_overlap

        # one undo must fully restore A to ~0 (proves drag == single history entry)
        page.get_by_title("撤销 (Ctrl/⌘+Z)").click(); page.wait_for_timeout(400)
        save()
        undone = video_clips()
        a_undone = next(c for c in undone if c.get("text_content") == "OverlapA")
        undo_ok = abs(a_undone["start_time"] - 0) <= 0.3
        print("UNDO_SINGLE_STEP", "PASS" if undo_ok else "FAIL",
              f"A.start={a_undone['start_time']} want~0 (was {a_after['start_time']} after drag)")
        ok = ok and undo_ok

        b.close()
    print("OVERALL", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
