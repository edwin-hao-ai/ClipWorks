"""Browser-based E2E check for ClipWorks video preview.

Requires Playwright and a running local stack:
  docker-compose up -d

Usage:
  cd backend && source .venv/bin/activate && cd .. && python scripts/browser_e2e_check.py
"""

import time
from playwright.sync_api import sync_playwright

BASE_URL = "http://localhost:3000"
PROJECT_ID = "517a2ad0-2818-4781-a902-236627e448f9"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, slow_mo=50)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        # 1. Login via POST to set cookie
        response = page.request.post("http://localhost:8000/auth/mock-login?provider=google")
        print("Login status:", response.status)
        cookies = context.cookies()
        print("Cookies after login:", cookies)

        # 2. Open project page
        page.goto(f"{BASE_URL}/projects/{PROJECT_ID}")
        print("Project page URL:", page.url)
        time.sleep(3)
        page.screenshot(path="/tmp/e2e_step1_open.png", full_page=True)

        # 3. Check video element
        video = page.locator("video").first
        print("Video visible:", video.is_visible())
        if not video.is_visible():
            print("FAIL: video element not visible")
            browser.close()
            return

        src = video.get_attribute("src")
        print("Video src:", src)
        # output_url 按设计存相对路径 /api/static/...（Next.js rewrites 代理到后端，
        # 见 AGENTS.md §7.2）；兼容旧的绝对后端 URL 格式。
        if not src or not (src.startswith("/api/static/") or src.startswith("http://localhost:8000")):
            print("FAIL: video src is neither /api/static/ relative path nor absolute backend URL")
            browser.close()
            return

        # 4. Play and verify
        page.evaluate("document.querySelector('video').play()")
        time.sleep(3)
        page.screenshot(path="/tmp/e2e_step2_playing.png", full_page=True)
        info = page.evaluate(
            """() => {
                const v = document.querySelector('video');
                return {
                    readyState: v.readyState,
                    currentTime: v.currentTime,
                    paused: v.paused,
                    duration: v.duration,
                    error: v.error ? v.error.code : null,
                };
            }"""
        )
        print("Video info:", info)

        if info["readyState"] >= 3 and info["duration"] > 0 and not info["error"]:
            print("PASS: video preview works")
        else:
            print("FAIL: video cannot play")

        browser.close()


if __name__ == "__main__":
    main()
