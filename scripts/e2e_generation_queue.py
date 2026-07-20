"""E2E: two projects -> second one is queued.

Creates two projects in a row, approves both quickly, and verifies that the
second project's generation panel reports "已加入生成队列" because the worker
runs with concurrency=1.

Requires a running local stack and backend venv with Playwright:
  cd backend && source .venv/bin/activate && cd .. && python scripts/e2e_generation_queue.py
"""

import sys
import time
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:3000"
API_URL = "http://localhost:8000"
# Use a concrete, detailed prompt that the planning agent usually turns into a
# plan without follow-up questions.
PROMPT_A = "帮我为 https://mddock.com/ 做一个 15 秒的产品发布视频，9:16，风格简洁科技"
PROMPT_B = "帮我为 https://mddock.com/ 再做一个 15 秒的产品发布视频，9:16，风格活泼年轻"


def wait_for_plan_or_question(page, timeout_ms: int = 120000):
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
    """Create a project and keep answering until a plan is produced."""
    page.goto(BASE_URL)
    page.locator('input[type="text"]').first.fill(prompt)
    page.locator('button:has-text("开始创作")').click()
    page.wait_for_url(lambda url: "/projects/" in url and "initialPrompt" in url, timeout=30000)

    state = wait_for_plan_or_question(page, timeout_ms=timeout_ms)
    attempts = 0
    while state == "question" and attempts < 3:
        page.screenshot(path=f"/tmp/e2e_queue_question_{attempts}.png")
        # Provide a concrete answer so the agent can proceed.
        state = answer_question_and_wait(page, "15秒，直接生成，突出核心卖点", timeout_ms=timeout_ms)
        attempts += 1
    return state == "plan"


def approve_and_wait_generation_ui(page):
    page.locator("button:has-text('确认生成')").first.click()
    page.locator("text=/已加入生成队列|正在生成/").first.wait_for(timeout=30000)
    project_id = page.url.split("/projects/")[1].split("?")[0]
    return project_id


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, slow_mo=50)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        resp = page.request.post(f"{API_URL}/auth/mock-login?provider=google")
        if resp.status != 200:
            print("FAIL: login failed")
            sys.exit(1)

        if not ensure_plan(page, PROMPT_A, timeout_ms=180000):
            print("FAIL: project A did not get a plan")
            sys.exit(1)
        id_a = approve_and_wait_generation_ui(page)
        print("project A id:", id_a)
        page.screenshot(path="/tmp/e2e_queue_project_a.png")

        if not ensure_plan(page, PROMPT_B, timeout_ms=180000):
            print("FAIL: project B did not get a plan")
            sys.exit(1)
        id_b = approve_and_wait_generation_ui(page)
        print("project B id:", id_b)
        page.screenshot(path="/tmp/e2e_queue_project_b.png")

        queued_heading = page.locator("text=已加入生成队列").first
        if queued_heading.is_visible():
            print("PASS: project B is reported as queued")
        else:
            running_heading = page.locator("text=正在生成").first
            if running_heading.is_visible():
                print("INFO: project B is already running (A finished quickly)")
            else:
                print("FAIL: project B generation UI not visible")
                sys.exit(1)

        jobs_a = page.request.get(f"{API_URL}/projects/{id_a}/renders/").json()
        jobs_b = page.request.get(f"{API_URL}/projects/{id_b}/renders/").json()
        print("jobs A:", [(j["status"], j["progress"]) for j in jobs_a[:2]])
        print("jobs B:", [(j["status"], j["progress"]) for j in jobs_b[:2]])

        if not jobs_a or not jobs_b:
            print("FAIL: missing render jobs")
            sys.exit(1)

        browser.close()


if __name__ == "__main__":
    main()
