"""Verify the workspace '用当前时间线重新渲染' button queues a new render job.

Self-contained: uses the isolated demo@e2e account (10 credits) so the 0-credit
hard gate on the demo@google account does not interfere. Creates its own project,
waits for the first render to reach a terminal state, then clicks the re-render
button and asserts a NEW job was queued.

Run: .e2e-venv/bin/python scripts/e2e_rerender.py
"""
import json
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
API = "http://localhost:8000"
OUT = Path("/Users/edwinhao/ClipWorks/data/e2e_audit")


def main():
    ok = True
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        ctx.request.post(f"{API}/auth/mock-login?provider=e2e")
        page = ctx.new_page(); page.set_default_timeout(30000)

        def new_project(title):
            r = ctx.request.post(
                f"{API}/projects/",
                headers={"Content-Type": "application/json"},
                data=json.dumps({"title": title, "source_url": "", "source_type": "url"}),
            )
            return r.json()["id"]

        pid = new_project("e2e-rerender-selfcontained")
        first = ctx.request.post(f"{API}/projects/{pid}/renders/generate")
        if not first.ok:
            print("RERENDER", "FAIL", f"initial generate rejected: {first.status} {first.text()}")
            b.close(); sys.exit(1)
        first_jid = first.json()["job_id"]

        # Wait until the project leaves 'generating' (render reached a terminal
        # state). The re-render button renders whenever there is a latest job and
        # the project is not generating, so success OR failure both qualify.
        # 本环境一次完整渲染约 ~227s（worker 两次 Kimi 调用 timeout 走 fallback ~120s + remotion 渲染），
        # 180s 不够；放宽到 420s 让首次渲染能到达 terminal。
        deadline = time.time() + 420
        terminal = None
        while time.time() < deadline:
            proj = ctx.request.get(f"{API}/projects/{pid}").json()
            if proj.get("status") != "generating":
                terminal = proj.get("status"); break
            time.sleep(3)
        if terminal is None:
            print("RERENDER", "FAIL", "initial render did not finish within 180s")
            b.close(); sys.exit(1)
        print("INITIAL_DONE", terminal, f"job={first_jid[:8]}")

        before = ctx.request.get(f"{API}/projects/{pid}/renders/").json()
        before_n = len(before)

        page.goto(f"{BASE}/projects/{pid}", wait_until="domcontentloaded")
        try: page.wait_for_load_state("networkidle", timeout=10000)
        except Exception: pass
        page.wait_for_timeout(2500)

        btn = page.get_by_role("button", name="用当前时间线重新渲染")
        try:
            btn.wait_for(state="visible", timeout=15000)
        except Exception:
            page.screenshot(path=str(OUT / "rerender_no_button.png"), full_page=True)
            print("RERENDER", "FAIL", "re-render button not visible")
            b.close(); sys.exit(1)
        btn.click()
        page.wait_for_timeout(3500)
        page.screenshot(path=str(OUT / "rerender.png"), full_page=True)

        after = ctx.request.get(f"{API}/projects/{pid}/renders/").json()
        after_n = len(after)
        new_latest = after[0]["id"] if after else None
        new_status = after[0]["status"] if after else None
        queued = (after_n > before_n) and (new_latest != first_jid) and (new_status in ("queued", "running", "completed"))
        print("RERENDER", "PASS" if queued else "FAIL",
              f"jobs {before_n}->{after_n}, latest={new_latest[:8] if new_latest else None}, status={new_status}")
        ok = ok and queued
        b.close()

    print("OVERALL", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
