"""Verify editor split-at-playhead and undo/redo, persisted via Save.

Run: .e2e-venv/bin/python scripts/e2e_split_undo.py
"""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
API = "http://localhost:8000"
OUT = Path("/Users/edwinhao/ClipWorks/data/e2e_audit")
PPS = 24


def main():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        ctx.request.post(f"{API}/auth/mock-login?provider=google")
        page = ctx.new_page(); page.set_default_timeout(20000)
        fresh = ctx.request.post(f"{API}/projects/", headers={"Content-Type": "application/json"},
                                 data=json.dumps({"title": "e2e-split", "source_url": "", "source_type": "url"}))
        pid = fresh.json()["id"]

        def comp():
            return ctx.request.get(f"{API}/compositions/{pid}").json()
        def api_clips_named(name):
            out = []
            for t in comp()["tracks"]:
                for c in t["clips"]:
                    if c.get("text_content") == name:
                        out.append(c)
            return out
        def dom_clips_named(name):
            return page.locator("div.absolute.top-1\\.5", has_text=name).count()
        def save():
            page.get_by_role("button", name="保存").click(); page.wait_for_timeout(1600)

        page.goto(f"{BASE}/projects/{pid}/editor", wait_until="domcontentloaded")
        try: page.wait_for_load_state("networkidle", timeout=10000)
        except Exception: pass
        page.wait_for_timeout(1500)

        base = api_clips_named("ClipWorks")
        assert len(base) >= 1, "need a ClipWorks clip"
        target = base[0]
        mid = round(target["start_time"] + target["duration"] / 2, 1)

        # select the clip (click the clip block directly; the text span is pointer-events:none)
        page.locator("div.absolute.top-1\\.5").first.click(); page.wait_for_timeout(300)
        ruler = page.locator("div.relative.h-8").first
        ruler.click(position={"x": mid * PPS, "y": 4}); page.wait_for_timeout(300)

        # split at playhead (local history), then verify undo/redo purely in the DOM
        page.get_by_role("button", name="分割").click(); page.wait_for_timeout(400)
        dom_split = dom_clips_named("ClipWorks")
        print("SPLIT(local)", "PASS" if dom_split == 2 else "FAIL", f"dom_clips={dom_split}")

        page.get_by_title("撤销 (Ctrl/⌘+Z)").click(); page.wait_for_timeout(300)
        dom_undo = dom_clips_named("ClipWorks")
        print("UNDO(local)", "PASS" if dom_undo == 1 else "FAIL", f"dom_clips={dom_undo}")

        page.get_by_title("重做 (Ctrl/⌘+Shift+Z)").click(); page.wait_for_timeout(300)
        dom_redo = dom_clips_named("ClipWorks")
        print("REDO(local)", "PASS" if dom_redo == 2 else "FAIL", f"dom_clips={dom_redo}")

        # persist the redone (2-clip) state and verify the API boundary
        save()
        after = api_clips_named("ClipWorks")
        boundary_ok = len(after) == 2 and abs(sorted(after, key=lambda c: c["start_time"])[1]["start_time"] - mid) < 0.15
        page.screenshot(path=str(OUT / "split_undo_editor.png"), full_page=True)
        print("PERSIST", "PASS" if boundary_ok else "FAIL",
              f"clips={len(after)} boundary≈{sorted(after, key=lambda c: c['start_time'])[1]['start_time'] if len(after)==2 else None} want≈{mid}")
        b.close()


if __name__ == "__main__":
    main()
