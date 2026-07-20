"""Verify '加入时间线' writes an asset as a clip into the composition.

Run: .e2e-venv/bin/python scripts/e2e_asset_to_timeline.py
"""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
API = "http://localhost:8000"
OUT = Path("/Users/edwinhao/ClipWorks/data/e2e_audit")


def main():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1280, "height": 900})
        ctx.request.post(f"{API}/auth/mock-login?provider=google")
        fresh = ctx.request.post(f"{API}/projects/", headers={"Content-Type": "application/json"},
                                 data=json.dumps({"title": "e2e-asset-tl", "source_url": "", "source_type": "url"}))
        pid = fresh.json()["id"]
        page = ctx.new_page(); page.set_default_timeout(20000)

        page.goto(f"{BASE}/projects/{pid}/assets", wait_until="domcontentloaded")
        try: page.wait_for_load_state("networkidle", timeout=10000)
        except Exception: pass
        page.wait_for_timeout(1200)

        page.locator("input[type=file]").first.set_input_files(str(OUT / "tiny.png"))
        page.wait_for_timeout(2500)
        assets = ctx.request.get(f"{API}/projects/{pid}/assets/").json()
        asset = next((a for a in assets if a.get("original_url") == "tiny.png"), None)
        assert asset, "uploaded asset not found"
        aid, atype = asset["id"], asset["type"]

        page.get_by_role("button", name="加入时间线").first.click()
        page.wait_for_timeout(2500)
        page.screenshot(path=str(OUT / "asset_to_timeline.png"), full_page=True)

        comp = ctx.request.get(f"{API}/compositions/{pid}").json()
        found = None
        for t in comp["tracks"]:
            for c in t["clips"]:
                if c.get("asset_id") == aid:
                    found = (t["type"], c); break
            if found: break
        ok = found is not None and found[0] == atype
        print("ADD_TO_TIMELINE", "PASS" if ok else "FAIL",
              f"asset_type={atype} placed_on={found[0] if found else None} clip={found[1] if found else None}")
        b.close()


if __name__ == "__main__":
    main()
