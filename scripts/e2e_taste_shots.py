"""taste-skill 视觉审计截图：全页面 × 深浅主题 × 桌面/移动。"""
import os
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
OUT = "data/e2e_audit/taste"
PID = "fc04330d-8cc1-4dce-98d5-f431eb38aae5"  # demo@google.com 的 ready 项目

PAGES = [
    ("login", "/login", False),
    ("home", "/", True),
    ("projects", "/projects", True),
    ("workspace", f"/projects/{PID}", True),
    ("editor", f"/projects/{PID}/editor", True),
    ("assets", f"/projects/{PID}/assets", True),
    ("settings", "/settings", True),
    ("billing", "/billing", True),
    ("notfound", "/this-page-does-not-exist", True),
]


def shoot(ctx, theme, vw, suffix):
    os.makedirs(OUT, exist_ok=True)
    page = ctx.new_page()
    page.set_viewport_size(vw)
    if theme == "light":
        page.add_init_script("window.localStorage.setItem('cw_theme','light')")
    for name, path, _needs_auth in PAGES:
        try:
            page.goto(BASE + path, wait_until="networkidle", timeout=30000)
        except Exception:
            try:
                page.goto(BASE + path, wait_until="domcontentloaded", timeout=30000)
            except Exception as e:
                print(f"FAIL {name}: {e}")
                continue
        page.wait_for_timeout(1200)
        page.screenshot(path=f"{OUT}/{name}_{theme}_{suffix}.png", full_page=False)
        print(f"shot {name}_{theme}_{suffix}")
    page.close()


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        # 登录
        page = ctx.new_page()
        page.goto(BASE + "/login", wait_until="domcontentloaded")
        page.screenshot(path=f"{OUT}/login_dark_desktop.png")
        print("shot login_dark_desktop")
        page.get_by_text("使用 Google 登录").click(timeout=5000)
        try:
            page.wait_for_url(lambda u: "/login" not in u, timeout=15000)
        except Exception:
            pass
        page.wait_for_timeout(1500)
        page.close()

        for theme in ("dark", "light"):
            shoot(ctx, theme, {"width": 1440, "height": 900}, "desktop")
        # 移动端抽查：首页 + 项目列表（深色即可）
        shoot(ctx, "dark", {"width": 390, "height": 844}, "mobile")
        browser.close()


if __name__ == "__main__":
    main()
