"""taste-skill 视觉审计截图 v2：等加载完成再截，补 light/mobile。"""
import os
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
OUT = "data/e2e_audit/taste"
PID = "fc04330d-8cc1-4dce-98d5-f431eb38aae5"

DARK_PAGES = [
    ("projects", "/projects"),
    ("workspace", f"/projects/{PID}"),
    ("editor", f"/projects/{PID}/editor"),
]
LIGHT_PAGES = [
    ("home", "/"),
    ("projects", "/projects"),
    ("workspace", f"/projects/{PID}"),
    ("editor", f"/projects/{PID}/editor"),
    ("assets", f"/projects/{PID}/assets"),
    ("settings", "/settings"),
    ("billing", "/billing"),
]
MOBILE_PAGES = [
    ("home", "/"),
    ("projects", "/projects"),
]


def settle(page):
    # 等加载占位消失（AuthGuard/数据加载），最多 45s
    try:
        page.wait_for_function(
            "() => !document.body.innerText.includes('加载中')",
            timeout=45000,
        )
    except Exception:
        pass
    page.wait_for_timeout(1500)


def shoot(ctx, pages, theme, vw, suffix):
    page = ctx.new_page()
    page.set_viewport_size(vw)
    if theme == "light":
        page.add_init_script("window.localStorage.setItem('cw_theme','light')")
    for name, path in pages:
        try:
            page.goto(BASE + path, wait_until="domcontentloaded", timeout=60000)
            settle(page)
            page.screenshot(path=f"{OUT}/{name}_{theme}_{suffix}.png")
            print(f"shot {name}_{theme}_{suffix}", flush=True)
        except Exception as e:
            print(f"FAIL {name}_{theme}_{suffix}: {str(e)[:100]}", flush=True)
    page.close()


def main():
    os.makedirs(OUT, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        page.goto(BASE + "/login", wait_until="domcontentloaded")
        page.get_by_text("使用 Google 登录").click(timeout=10000)
        try:
            page.wait_for_url(lambda u: "/login" not in u, timeout=20000)
        except Exception:
            pass
        page.wait_for_timeout(2000)
        page.close()
        print("logged in", flush=True)

        shoot(ctx, DARK_PAGES, "dark", {"width": 1440, "height": 900}, "desktop")
        shoot(ctx, LIGHT_PAGES, "light", {"width": 1440, "height": 900}, "desktop")
        shoot(ctx, MOBILE_PAGES, "dark", {"width": 390, "height": 844}, "mobile")
        browser.close()
        print("DONE", flush=True)


if __name__ == "__main__":
    main()
