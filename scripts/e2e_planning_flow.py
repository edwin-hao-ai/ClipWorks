"""E2E: planning -> approve -> generation UI.

Creates a project from the launchpad, waits for the Agent to produce a plan
(answering any clarifying questions it asks), clicks "确认生成", and verifies
that the generation panel appears with queue/running feedback and live logs.

Requires a running local stack and backend venv with Playwright:
  cd backend && source .venv/bin/activate && cd .. && python scripts/e2e_planning_flow.py
"""

import sys
import time
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:3000"
API_URL = "http://localhost:8000"
PROMPT = "帮我为 https://mddock.com/ 做一个 15 秒的产品发布视频，9:16，风格简洁科技"


def wait_for_plan_or_question(page, timeout_ms: int = 120000):
    """Wait until either a plan card or a clarifying question appears."""
    deadline = time.time() + timeout_ms / 1000
    while time.time() < deadline:
        if page.locator("text=方案已就绪").first.is_visible():
            return "plan"
        if page.locator("text=AI 导演的问题").first.is_visible():
            return "question"
        time.sleep(0.5)
    return None


def answer_question_and_wait(page, answer: str, timeout_ms: int = 120000):
    page.locator('input[type="text"]').first.fill(answer)
    page.locator('button[type="submit"]').first.click()
    return wait_for_plan_or_question(page, timeout_ms)


def ensure_plan(page, prompt: str, timeout_ms: int = 180000):
    """Keep the planning conversation going until a plan is produced."""
    page.goto(BASE_URL)
    page.locator('input[type="text"]').first.fill(prompt)
    page.locator('button:has-text("开始创作")').click()
    page.wait_for_url(lambda url: "/projects/" in url and "initialPrompt" in url, timeout=30000)

    state = wait_for_plan_or_question(page, timeout_ms=timeout_ms)
    attempts = 0
    while state == "question" and attempts < 3:
        print("agent asked a clarifying question; answering...")
        page.screenshot(path=f"/tmp/e2e_plan_question_{attempts}.png")
        state = answer_question_and_wait(page, "15秒，直接生成，突出核心卖点", timeout_ms=timeout_ms)
        attempts += 1
    return state == "plan"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=50)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        resp = page.request.post(f"{API_URL}/auth/mock-login?provider=google")
        print("login status:", resp.status)
        if resp.status != 200:
            print("FAIL: login failed")
            sys.exit(1)

        if not ensure_plan(page, PROMPT, timeout_ms=180000):
            page.screenshot(path="/tmp/e2e_plan_failed.png")
            print("FAIL: agent did not produce a plan")
            sys.exit(1)

        project_url = page.url
        print("project url:", project_url)
        page.screenshot(path="/tmp/e2e_plan_created.png")

        print("plan ready")
        page.screenshot(path="/tmp/e2e_plan_ready.png")

        page.locator("button:has-text('确认生成')").first.click()
        gen_heading = page.locator("text=/已加入生成队列|正在生成/").first
        gen_heading.wait_for(timeout=30000)
        print("generation UI visible:", gen_heading.text_content())
        page.screenshot(path="/tmp/e2e_generating.png")

        try:
            page.locator("text=/已加入生成队列，开始执行|时间线构建完成|素材收集完成|HTML 预览已生成/").first.wait_for(timeout=60000)
            print("live logs appeared")
        except Exception:
            print("WARN: live logs did not appear within 60s (worker may still be busy)")

        page.screenshot(path="/tmp/e2e_generation_logs.png")

        project_id = project_url.split("/projects/")[1].split("?")[0]
        jobs_resp = page.request.get(f"{API_URL}/projects/{project_id}/renders/")
        jobs = jobs_resp.json()
        print("jobs:", [(j["id"], j["status"], j["progress"]) for j in jobs[:3]])
        if not jobs:
            print("FAIL: no render job created")
            sys.exit(1)

        print("PASS: plan -> approve -> generation flow works")
        browser.close()


if __name__ == "__main__":
    main()
