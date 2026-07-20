"""Verify the TopBar credits badge reflects real remaining credits.

Run: .e2e-venv/bin/python scripts/e2e_credits_badge.py
"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
API = "http://localhost:8000"
OUT = Path("/Users/edwinhao/ClipWorks/data/e2e_audit")


def main():
    ok = True
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        ctx.request.post(f"{API}/auth/mock-login?provider=google")
        page = ctx.new_page(); page.set_default_timeout(20000)

        credits = ctx.request.get(f"{API}/auth/me/stats").json()["remaining_credits"]

        page.goto(f"{BASE}/projects", wait_until="domcontentloaded")
        try: page.wait_for_load_state("networkidle", timeout=10000)
        except Exception: pass

        badge = page.get_by_test_id("credits-badge")
        badge.wait_for(state="visible", timeout=12000)
        shown = page.get_by_test_id("credits-value").inner_text().strip()
        href = badge.get_attribute("href") or ""
        cls = badge.get_attribute("class") or ""

        value_ok = shown == str(credits)
        print("BADGE_VALUE", "PASS" if value_ok else "FAIL", f"shown={shown!r} stats={credits}")
        ok = ok and value_ok

        link_ok = href.endswith("/billing")
        print("BADGE_LINK", "PASS" if link_ok else "FAIL", f"href={href!r}")
        ok = ok and link_ok

        # when credits are depleted the badge must use the error (red) styling
        if credits == 0:
            red_ok = "text-error" in cls
            print("BADGE_DEPLETED_STYLE", "PASS" if red_ok else "FAIL", "class does not include text-error")
            ok = ok and red_ok
        else:
            print("BADGE_DEPLETED_STYLE", "SKIP", f"credits={credits}")

        page.screenshot(path=str(OUT / "credits_badge.png"), full_page=True)
        b.close()
    print("OVERALL", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
