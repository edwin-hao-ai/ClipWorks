"""隔离复测「退出登录」跳转：登录 -> /projects -> 点侧栏退出登录 -> 等 /login。
连跑 3 轮，报告每轮跳转耗时，用于判断审计里的 logout FAIL 是计时 flake 还是真回归。
"""
import time

from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
API = "http://localhost:8000"


def run_round(browser, idx):
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()
    # mock 登录（与审计脚本一致：直接打后端拿 cookie）
    resp = ctx.request.post(f"{API}/auth/mock-login?provider=google")
    assert resp.ok, f"login api failed: {resp.status}"
    page.goto(f"{BASE}/projects", wait_until="domcontentloaded", timeout=30000)
    page.wait_for_timeout(1500)
    t0 = time.time()
    page.get_by_role("button", name="退出登录").first.click(timeout=5000)
    try:
        page.wait_for_url(lambda u: "/login" in u, timeout=8000)
        dt = time.time() - t0
        me = ctx.request.get(f"{API}/auth/me")
        print(f"round {idx}: PASS redirect={dt:.2f}s /auth/me={me.status}")
        ok = True
    except Exception as e:
        dt = time.time() - t0
        me = ctx.request.get(f"{API}/auth/me")
        print(f"round {idx}: FAIL after {dt:.2f}s url={page.url} /auth/me={me.status} :: {str(e)[:80]}")
        ok = False
    ctx.close()
    return ok


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        results = [run_round(browser, i + 1) for i in range(3)]
        browser.close()
    print(f"=== {sum(results)}/3 passed ===")


if __name__ == "__main__":
    main()
