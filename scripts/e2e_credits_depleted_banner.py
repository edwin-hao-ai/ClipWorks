"""Verify the workspace surfaces an honest 'credits depleted' banner at 0 credits.

The shared demo user is currently at 0 credits, so the banner must appear and
link to /billing. (Soft surfacing: generation is not blocked in this demo.)

Run: .e2e-venv/bin/python scripts/e2e_credits_depleted_banner.py
"""
import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
API = "http://localhost:8000"
OUT = Path("/Users/edwinhao/ClipWorks/data/e2e_audit")


def main():
    ok = True
    created = None
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        ctx.request.post(f"{API}/auth/mock-login?provider=google")
        page = ctx.new_page(); page.set_default_timeout(20000)

        credits = ctx.request.get(f"{API}/auth/me/stats").json()["remaining_credits"]

        fresh = ctx.request.post(
            f"{API}/projects/",
            headers={"Content-Type": "application/json"},
            data=json.dumps({"title": "e2e-credits-banner", "source_url": "", "source_type": "url"}),
        )
        created = fresh.json()["id"]

        page.goto(f"{BASE}/projects/{created}", wait_until="domcontentloaded")
        try: page.wait_for_load_state("networkidle", timeout=10000)
        except Exception: pass

        if credits == 0:
            banner = page.get_by_test_id("credits-depleted-banner")
            banner.wait_for(state="visible", timeout=12000)
            link = banner.get_by_role("link", name="前往计费页")
            href = link.get_attribute("href") or ""
            shown_ok = banner.is_visible()
            link_ok = href.endswith("/billing")
            print("BANNER_SHOWN", "PASS" if shown_ok else "FAIL")
            print("BANNER_LINK", "PASS" if link_ok else "FAIL", f"href={href!r}")
            ok = ok and shown_ok and link_ok
        else:
            banner = page.get_by_test_id("credits-depleted-banner")
            hidden_ok = not banner.is_visible()
            print("BANNER_HIDDEN_WHEN_CREDITS", "PASS" if hidden_ok else "FAIL", f"credits={credits}")
            ok = ok and hidden_ok

        page.screenshot(path=str(OUT / "credits_depleted_banner.png"), full_page=True)
        b.close()

    if created:
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            ctx = b.new_context()
            ctx.request.post(f"{API}/auth/mock-login?provider=google")
            try: ctx.request.delete(f"{API}/projects/{created}")
            except Exception: pass
            b.close()

    print("OVERALL", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
