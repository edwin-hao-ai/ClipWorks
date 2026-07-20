"""Re-verify the FIXES against the running hot-reloaded stack.

Confirms the originally-broken E2E findings are now actually fixed:
  F1 素材库 link no longer 404
  F2 anonymous home create redirects to /login (no 401 banner)
  F3 editor can edit/add/delete clips and Save PERSISTS the change
  F4 asset delete works (upload -> delete -> count decreases)
  F5 logout clears the server session cookie (/auth/me -> 401 after)

Run: .e2e-venv/bin/python scripts/e2e_reverify.py
"""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
API = "http://localhost:8000"
OUT = Path("/Users/edwinhao/ClipWorks/data/e2e_audit")
R = []


def rec(n, s, d=""):
    R.append({"name": n, "status": s, "detail": d})
    print(f"[{s:5}] {n} :: {d}")


def netidle(page):
    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except Exception:
        pass


def main():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        ctx.request.post(f"{API}/auth/mock-login?provider=google")
        page = ctx.new_page()
        page.set_default_timeout(20000)
        page.on("dialog", lambda d: d.accept())

        projects = ctx.request.get(f"{API}/projects/").json()
        pid = projects[0]["id"]

        # F1: 素材库 link
        page.goto(f"{BASE}/", wait_until="domcontentloaded"); netidle(page)
        page.get_by_role("link", name="素材库").click()
        page.wait_for_timeout(1500); netidle(page)
        ok = page.url.rstrip("/").endswith("/projects") and "404" not in page.inner_text("body")
        page.screenshot(path=str(OUT / "reverify_F1_nav.png"), full_page=True)
        rec("F1 素材库 link fixed", "PASS" if ok else "FAIL", f"url={page.url}")

        # F3: editor edit/add/delete + persist
        comp = ctx.request.get(f"{API}/compositions/{pid}").json()
        target_clip = comp["tracks"][0]["clips"][0]
        tcid = target_clip["id"]
        new_dur = round((target_clip["duration"] or 3) + 4.7, 1)

        page.goto(f"{BASE}/projects/{pid}/editor", wait_until="domcontentloaded"); netidle(page)
        page.wait_for_timeout(1500)
        # select the first clip block
        page.locator("div.absolute.top-1\\.5").first.click()
        page.wait_for_timeout(500)
        # set duration (2nd number input) to new_dur
        page.locator('input[type=number]').nth(1).fill(str(new_dur))
        page.get_by_role("button", name="保存").click()
        page.wait_for_timeout(1500)
        after = ctx.request.get(f"{API}/compositions/{pid}").json()
        saved_clip = next((c for t in after["tracks"] for c in t["clips"] if c["id"] == tcid), None)
        edit_ok = saved_clip and abs(saved_clip["duration"] - new_dur) < 0.05
        page.screenshot(path=str(OUT / "reverify_F3_edit.png"), full_page=True)
        rec("F3a editor edit duration persists", "PASS" if edit_ok else "FAIL",
            f"duration before={target_clip['duration']} -> after={saved_clip and saved_clip['duration']} (want {new_dur})")

        # add a clip to first track then save
        page.goto(f"{BASE}/projects/{pid}/editor", wait_until="domcontentloaded"); netidle(page)
        page.wait_for_timeout(1200)
        before_count = sum(len(t["clips"]) for t in ctx.request.get(f"{API}/compositions/{pid}").json()["tracks"])
        page.get_by_text("添加片段").first.click()
        page.wait_for_timeout(400)
        page.get_by_role("button", name="保存").click()
        page.wait_for_timeout(1500)
        after_add = ctx.request.get(f"{API}/compositions/{pid}").json()
        add_count = sum(len(t["clips"]) for t in after_add["tracks"])
        add_ok = add_count == before_count + 1
        rec("F3b editor add clip persists", "PASS" if add_ok else "FAIL",
            f"clips {before_count} -> {add_count}")

        # delete the last clip of first track then save
        page.goto(f"{BASE}/projects/{pid}/editor", wait_until="domcontentloaded"); netidle(page)
        page.wait_for_timeout(1200)
        page.locator("div.absolute.top-1\\.5").last.click()
        page.wait_for_timeout(400)
        page.get_by_text("删除片段").click()
        page.wait_for_timeout(400)
        page.get_by_role("button", name="保存").click()
        page.wait_for_timeout(1500)
        after_del = ctx.request.get(f"{API}/compositions/{pid}").json()
        del_count = sum(len(t["clips"]) for t in after_del["tracks"])
        del_ok = del_count == add_count - 1
        rec("F3c editor delete clip persists", "PASS" if del_ok else "FAIL",
            f"clips {add_count} -> {del_count}")

        # F4: asset delete
        page.goto(f"{BASE}/projects/{pid}/assets", wait_until="domcontentloaded"); netidle(page)
        page.wait_for_timeout(1000)
        b0 = len(ctx.request.get(f"{API}/projects/{pid}/assets/").json())
        page.locator("input[type=file]").first.set_input_files(str(OUT / "tiny.png"))
        page.wait_for_timeout(2500)
        b1 = len(ctx.request.get(f"{API}/projects/{pid}/assets/").json())
        # delete the newest tile's 删除 button
        try:
            tile = page.locator("text=tiny.png").first
            tile.hover()
            page.wait_for_timeout(300)
        except Exception:
            pass
        page.get_by_role("button", name="删除").first.click()
        page.wait_for_timeout(2000)
        b2 = len(ctx.request.get(f"{API}/projects/{pid}/assets/").json())
        page.screenshot(path=str(OUT / "reverify_F4_assets.png"), full_page=True)
        rec("F4 asset delete works", "PASS" if (b1 > b0 and b2 == b0) else "FAIL",
            f"assets {b0} -> {b1} (upload) -> {b2} (delete)")

        # F5: logout clears cookie
        page.goto(f"{BASE}/projects", wait_until="domcontentloaded"); netidle(page)
        page.get_by_text("退出登录").click()
        page.wait_for_timeout(1500)
        me = ctx.request.get(f"{API}/auth/me")
        page.screenshot(path=str(OUT / "reverify_F5_logout.png"), full_page=True)
        rec("F5 logout clears session", "PASS" if me.status == 401 else "FAIL",
            f"/auth/me after logout -> {me.status} (want 401)")

        # F2: anonymous create redirects to /login
        ctx2 = b.new_context(viewport={"width": 1440, "height": 900})
        p2 = ctx2.new_page(); p2.set_default_timeout(20000)
        p2.goto(f"{BASE}/", wait_until="domcontentloaded"); netidle(p2)
        p2.locator('input[placeholder^="例如"]').fill("未登录创建")
        p2.get_by_role("button", name="开始创作").click()
        p2.wait_for_timeout(2500)
        p2.screenshot(path=str(OUT / "reverify_F2_anon.png"), full_page=True)
        rec("F2 anonymous create -> /login", "PASS" if "/login" in p2.url else "FAIL",
            f"url={p2.url}")

        (OUT / "reverify.json").write_text(json.dumps(R, ensure_ascii=False, indent=2))
        from collections import Counter
        print("\n=== TALLY ===", dict(Counter(r["status"] for r in R)))
        b.close()


if __name__ == "__main__":
    main()
