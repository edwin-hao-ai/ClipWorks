"""Verify the core AI planning -> approve loop on a fresh project (KIMI key present)."""
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
API = "http://localhost:8000"
OUT = Path("/Users/edwinhao/ClipWorks/data/e2e_audit")

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    ctx = b.new_context(viewport={"width": 1440, "height": 900})
    ctx.request.post(f"{API}/auth/mock-login?provider=google")
    fresh = ctx.request.post(
        f"{API}/projects/",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"title": "E2E 规划验证", "source_url": "", "source_type": "url",
                         "target_format": "9:16", "target_duration": 15}),
    )
    print("create status", fresh.status, fresh.text()[:200])
    fpid = fresh.json()["id"]
    page = ctx.new_page()
    page.set_default_timeout(20000)
    page.goto(f"{BASE}/projects/{fpid}", wait_until="domcontentloaded")
    try:
        page.wait_for_load_state("networkidle", timeout=10000)
    except Exception:
        pass
    page.wait_for_timeout(2500)
    ta = page.locator("textarea").first
    ta.wait_for(state="visible", timeout=10000)
    ta.fill("请规划 4 个镜头，15 秒，9:16，活泼风格的产品介绍视频")
    ta.press("Enter")
    deadline = time.time() + 90
    outcome = "timeout"
    while time.time() < deadline:
        txt = page.inner_text("body")
        if "确认生成" in txt:
            outcome = "plan_ready_approve_visible"
            break
        if "响应失败" in txt or "Agent 响应失败" in txt:
            outcome = "agent_failed_no_fallback"
            break
        page.wait_for_timeout(2000)
    page.screenshot(path=str(OUT / "v_E_planning.png"), full_page=True)
    print("PLAN_OUTCOME", outcome, "after", round(90 - (deadline - time.time()), 1), "s")
    # If approve visible, click it to confirm generation enqueues
    if outcome == "plan_ready_approve_visible":
        try:
            page.get_by_text("确认生成").first.click()
            page.wait_for_timeout(4000)
            jobs = ctx.request.get(f"{API}/projects/{fpid}/renders/").json()
            print("APPROVE_ENQUEUED", len(jobs) if isinstance(jobs, list) else jobs,
                  "latest_status", jobs[0].get("status") if isinstance(jobs, list) and jobs else None)
            page.screenshot(path=str(OUT / "v_E_after_approve.png"), full_page=True)
        except Exception as e:
            print("APPROVE_CLICK_ERR", str(e)[:200])
    b.close()
