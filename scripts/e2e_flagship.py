"""Flagship happy-path E2E, run to COMPLETION in the browser.

The core product promise: one sentence -> plan -> approve -> real MP4 -> preview.
Existing scripts stop once the generation panel shows "running"; this one waits for
the render to actually finish and asserts a playable preview appears (or fails fast
on stalled/failed). Uses an isolated fresh account (provider=flagship, 10 credits)
so the 0-credit gate never interferes.

Run: .e2e-venv/bin/python scripts/e2e_flagship.py
"""
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
API = "http://localhost:8000"
OUT = Path("/Users/edwinhao/ClipWorks/data/e2e_audit")
PROMPT = "帮我为一款 AI 降噪耳机做 15 秒产品发布视频，9:16，风格简洁科技，核心卖点：40dB 主动降噪、36 小时续航、空间音频，直接生成"


def wait_for_plan_or_question(page, timeout_s=150):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if page.locator("text=方案已就绪").first.is_visible():
            return "plan"
        if page.locator("text=AI 导演的问题").first.is_visible():
            return "question"
        page.wait_for_timeout(1000)
    return None


def ensure_plan(page):
    page.goto(BASE)
    page.locator('input[type="text"]').first.fill(PROMPT)
    page.locator('button:has-text("开始创作")').click()
    page.wait_for_url(lambda u: "/projects/" in u and "initialPrompt" in u, timeout=30000)
    state = wait_for_plan_or_question(page)
    attempts = 0
    while state == "question" and attempts < 3:
        # 等待输入框重新可用（流式结束后 loading 才清零），用更长超时容忍 SSE 刷新延迟。
        box = page.locator('input[type="text"]').first
        box.fill("15秒，直接生成，突出核心卖点", timeout=90000)
        page.locator('button[type="submit"]').first.click()
        state = wait_for_plan_or_question(page)
        attempts += 1
    return state == "plan"


def main():
    ok = True
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        ctx.request.post(f"{API}/auth/mock-login?provider=flagship")
        page = ctx.new_page(); page.set_default_timeout(30000)

        if not ensure_plan(page):
            page.screenshot(path=str(OUT / "flagship_no_plan.png"), full_page=True)
            print("PLAN", "FAIL", "agent did not produce a plan")
            b.close(); sys.exit(1)
        print("PLAN", "PASS")
        pid = page.url.split("/projects/")[1].split("?")[0]

        page.locator("button:has-text('确认生成')").first.click()
        try:
            page.locator("text=/已加入生成队列|正在生成|生成中/").first.wait_for(timeout=30000)
        except Exception:
            page.screenshot(path=str(OUT / "flagship_no_panel.png"), full_page=True)
            print("APPROVE", "FAIL", "generation panel did not appear")
            b.close(); sys.exit(1)
        print("APPROVE", "PASS", "generation panel visible")

        # Wait for the project to reach a terminal state via API (ground truth),
        # failing fast on a stalled/failed render.
        deadline = time.time() + 300
        final = None
        while time.time() < deadline:
            proj = ctx.request.get(f"{API}/projects/{pid}").json()
            st = proj.get("status")
            jobs = ctx.request.get(f"{API}/projects/{pid}/renders/").json()
            latest = jobs[0] if jobs else None
            lst = latest["status"] if latest else None
            if lst in ("completed", "failed") or st in ("ready", "failed"):
                final = (st, lst, latest); break
            page.wait_for_timeout(4000)
        st, lst, latest = final if final else (None, None, None)
        if st == "ready" and lst == "completed" and latest and latest.get("output_url"):
            placeholder = "sample.mp4" in latest["output_url"]
            print("RENDER_COMPLETE", "PASS" if not placeholder else "WARN",
                  f"status={st} job={lst} placeholder={placeholder} progress={latest.get('progress')}")
            ok = ok and not placeholder
        else:
            page.screenshot(path=str(OUT / "flagship_not_ready.png"), full_page=True)
            print("RENDER_COMPLETE", "FAIL",
                  f"status={st} job={lst} latest={latest if not latest else {k:latest.get(k) for k in ('status','progress','error_message')}}")
            b.close(); sys.exit(1)

        # UI should now show a preview (video or html) and the workspace (ready).
        page.goto(f"{BASE}/projects/{pid}", wait_until="domcontentloaded")
        try: page.wait_for_load_state("networkidle", timeout=10000)
        except Exception: pass
        page.wait_for_timeout(3000)
        has_preview = page.locator("video").first.is_visible() or page.locator("iframe").first.is_visible()
        print("PREVIEW_VISIBLE", "PASS" if has_preview else "FAIL")
        ok = ok and has_preview
        page.screenshot(path=str(OUT / "flagship_done.png"), full_page=True)
        b.close()

    print("OVERALL", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
