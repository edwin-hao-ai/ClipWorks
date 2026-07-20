"""Verify the editor preview video is two-way bound to the timeline playhead.

- video -> playhead: setting video.currentTime + timeupdate advances the timeline
  playhead label (onTimeUpdate -> setCurrentTime -> Timeline header).
- playhead -> video: clicking the ruler seeks the playhead, which seeks the video
  (PreviewPlayer currentTime prop -> VideoPreview effect sets video.currentTime).

Uses a ready demo@google project with a REAL (non-placeholder) mp4 so the <video>
branch renders. No rendering is triggered.

Run: .e2e-venv/bin/python scripts/e2e_playhead_preview.py
"""
import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
API = "http://localhost:8000"
OUT = Path("/Users/edwinhao/ClipWorks/data/e2e_audit")


def read_playhead(page):
    txt = page.locator("span.font-mono").first.inner_text()
    m = re.search(r"([\d.]+)s\s*/", txt)
    return float(m.group(1)) if m else None


def main():
    ok = True
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        ctx.request.post(f"{API}/auth/mock-login?provider=google")
        page = ctx.new_page(); page.set_default_timeout(25000)

        # ready project with a real rendered mp4 (not the placeholder sample)
        pid = None
        for proj in ctx.request.get(f"{API}/projects/").json():
            if proj.get("status") != "ready":
                continue
            jobs = ctx.request.get(f"{API}/projects/{proj['id']}/renders/").json()
            if (isinstance(jobs, list) and jobs and jobs[0]["status"] == "completed"
                    and jobs[0].get("output_url") and "sample.mp4" not in jobs[0]["output_url"]):
                pid = proj["id"]; break
        if not pid:
            print("SETUP", "WARN", "no ready real-mp4 project; skipping")
            b.close(); sys.exit(0)
        print("SETUP", "PASS", f"project={pid[:8]}")

        page.goto(f"{BASE}/projects/{pid}/editor", wait_until="domcontentloaded")
        try: page.wait_for_load_state("networkidle", timeout=10000)
        except Exception: pass
        page.wait_for_timeout(2500)

        video = page.locator("video").first
        if not video.is_visible(timeout=8000):
            page.screenshot(path=str(OUT / "playhead_no_video.png"), full_page=True)
            print("VIDEO_PRESENT", "FAIL", "no <video> in editor preview")
            b.close(); sys.exit(1)
        print("VIDEO_PRESENT", "PASS")

        # Direction 1: video -> playhead
        page.locator("video").first.evaluate(
            "(v) => { v.currentTime = 2.5; v.dispatchEvent(new Event('timeupdate')); }"
        )
        page.wait_for_timeout(600)
        ph = read_playhead(page)
        d1 = ph is not None and abs(ph - 2.5) < 0.5
        print("VIDEO_TO_PLAYHEAD", "PASS" if d1 else "FAIL", f"playhead={ph} (want ~2.5)")
        ok = ok and d1

        # Direction 2: playhead (ruler click) -> video
        ruler = page.locator("div.relative.h-8").first
        box = ruler.bounding_box()
        if not box:
            print("PLAYHEAD_TO_VIDEO", "FAIL", "ruler not found")
            b.close(); sys.exit(1)
        # click ~300px into the ruler (scrollLeft=0), then read the resulting playhead
        ruler.click(position={"x": min(300, box["width"] - 10), "y": 10})
        page.wait_for_timeout(800)
        ph2 = read_playhead(page)
        vt = page.locator("video").first.evaluate("(v) => v.currentTime")
        d2 = ph2 is not None and abs(vt - ph2) < 0.6 and ph2 > 0.3
        print("PLAYHEAD_TO_VIDEO", "PASS" if d2 else "FAIL",
              f"playhead={ph2} video.currentTime={round(vt,2)}")
        ok = ok and d2

        page.screenshot(path=str(OUT / "playhead_preview.png"), full_page=True)
        b.close()

    print("OVERALL", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
