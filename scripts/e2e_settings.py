"""Verify Settings page persistence: display name (backend), theme + notifications (localStorage).

Run: .e2e-venv/bin/python scripts/e2e_settings.py
"""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
API = "http://localhost:8000"
OUT = Path("/Users/edwinhao/ClipWorks/data/e2e_audit")


def main():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1280, "height": 900})
        ctx.request.post(f"{API}/auth/mock-login?provider=google")
        orig_name = ctx.request.get(f"{API}/auth/me").json()["user"]["name"]
        page = ctx.new_page(); page.set_default_timeout(20000)

        page.goto(f"{BASE}/settings", wait_until="domcontentloaded")
        try: page.wait_for_load_state("networkidle", timeout=10000)
        except Exception: pass
        page.wait_for_timeout(1200)

        # 1) rename
        page.get_by_label("编辑昵称").click(); page.wait_for_timeout(200)
        box = page.locator("input[maxlength]").first
        box.fill("E2E 昵称")
        page.get_by_label("保存昵称").click(); page.wait_for_timeout(1800)
        new_name = ctx.request.get(f"{API}/auth/me").json()["user"]["name"]
        print("NAME_PERSIST", "PASS" if new_name == "E2E 昵称" else "FAIL", f"-> {new_name!r}")

        # 2) theme toggle -> light, persists across reload
        page.get_by_text("深色（点击切换浅色）").click(); page.wait_for_timeout(400)
        dt = page.evaluate("document.documentElement.dataset.theme || 'dark'")
        print("THEME_APPLY", "PASS" if dt == "light" else "FAIL", f"data-theme={dt}")
        page.reload(wait_until="domcontentloaded"); page.wait_for_timeout(1200)
        dt2 = page.evaluate("document.documentElement.dataset.theme || 'dark'")
        print("THEME_PERSIST", "PASS" if dt2 == "light" else "FAIL", f"after reload data-theme={dt2}")
        # set back to dark for cleanliness
        page.get_by_text("浅色（点击切换深色）").click(); page.wait_for_timeout(200)

        # 3) notifications toggle -> off, persists
        page.get_by_test_id("setting-value-通知").click(); page.wait_for_timeout(300)
        txt_off = page.get_by_test_id("setting-value-通知").inner_text()
        print("NOTIF_TOGGLE", "PASS" if "关闭" in txt_off else "FAIL", txt_off)
        page.reload(wait_until="domcontentloaded"); page.wait_for_timeout(1200)
        txt_off2 = page.get_by_test_id("setting-value-通知").inner_text()
        page.screenshot(path=str(OUT / "settings_light.png"), full_page=True)
        print("NOTIF_PERSIST", "PASS" if "关闭" in txt_off2 else "FAIL", txt_off2)

        # restore original name
        ctx.request.put(f"{API}/auth/me", headers={"Content-Type": "application/json"},
                        data=json.dumps({"name": orig_name}))
        b.close()


if __name__ == "__main__":
    main()
