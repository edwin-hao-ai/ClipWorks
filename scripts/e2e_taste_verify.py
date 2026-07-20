"""修复复验截图：主题持久化/项目封面/素材缩略图/404/移动端/片段着色。"""
import os
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
OUT = "data/e2e_audit/taste_fix"
UID = "e277eea9-9257-45ee-8276-43aec4535316"
PID = "fc04330d-8cc1-4dce-98d5-f431eb38aae5"

SHOTS = [
    # (name, path, theme, viewport)
    ("projects_light_desktop", "/projects", "light", (1440, 900)),
    ("assets_dark_desktop", f"/projects/{PID}/assets", "dark", (1440, 900)),
    ("notfound_dark_desktop", "/this-page-does-not-exist", "dark", (1440, 900)),
    ("editor_dark_desktop", f"/projects/{PID}/editor", "dark", (1440, 900)),
    ("projects_dark_mobile", "/projects", "dark", (390, 844)),
    ("home_dark_mobile", "/", "dark", (390, 844)),
]


def main():
    os.makedirs(OUT, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context()
        ctx.add_cookies([{"name": "session_user_id", "value": UID, "domain": "localhost", "path": "/"}])
        for name, path, theme, (w, h) in SHOTS:
            page = ctx.new_page()
            page.set_viewport_size({"width": w, "height": h})
            if theme == "light":
                page.add_init_script("window.localStorage.setItem('cw_theme','light')")
            try:
                page.goto(BASE + path, wait_until="domcontentloaded", timeout=60000)
                try:
                    page.wait_for_function(
                        "() => !document.body.innerText.includes('加载中')", timeout=45000
                    )
                except Exception:
                    pass
                page.wait_for_timeout(3500)  # 等封面图/缩略图加载
                page.screenshot(path=f"{OUT}/{name}.png")
                print("shot", name, flush=True)
            except Exception as e:
                print(f"FAIL {name}: {str(e)[:100]}", flush=True)
            page.close()
        browser.close()
        print("DONE", flush=True)


if __name__ == "__main__":
    main()
