"""Verify in-workspace project deletion with an inline confirm/cancel.

Run: .e2e-venv/bin/python scripts/e2e_delete_project.py
"""
import json
import re
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

        fresh = ctx.request.post(
            f"{API}/projects/",
            headers={"Content-Type": "application/json"},
            data=json.dumps({"title": "e2e-delete", "source_url": "", "source_type": "url"}),
        )
        pid = fresh.json()["id"]

        page.goto(f"{BASE}/projects/{pid}", wait_until="domcontentloaded")
        try: page.wait_for_load_state("networkidle", timeout=10000)
        except Exception: pass
        page.get_by_test_id("delete-project").wait_for(state="visible", timeout=12000)

        # first click arms the confirm; cancel should revert it
        page.get_by_test_id("delete-project").click()
        page.get_by_test_id("confirm-delete").wait_for(state="visible", timeout=6000)
        page.get_by_test_id("cancel-delete").click()
        page.wait_for_timeout(300)
        cancel_ok = page.get_by_test_id("delete-project").is_visible() and not page.get_by_test_id(
            "confirm-delete"
        ).is_visible()
        print("DELETE_CANCEL", "PASS" if cancel_ok else "FAIL")
        ok = ok and cancel_ok

        # arm + confirm -> navigates to list and the project is gone
        page.get_by_test_id("delete-project").click()
        page.get_by_test_id("confirm-delete").wait_for(state="visible", timeout=6000)
        page.get_by_test_id("confirm-delete").click()
        try:
            page.wait_for_url(re.compile(r".*/projects/?$"), timeout=12000)
        except Exception:
            pass
        navigated = re.search(r"/projects/?$", page.url) is not None
        print("DELETE_NAVIGATE", "PASS" if navigated else "FAIL", f"url={page.url}")
        ok = ok and navigated

        gone = ctx.request.get(f"{API}/projects/{pid}")
        deleted_ok = gone.status == 404
        print("DELETE_GONE", "PASS" if deleted_ok else "FAIL", f"GET /projects/{pid[:8]} -> {gone.status}")
        ok = ok and deleted_ok

        page.screenshot(path=str(OUT / "delete_project.png"), full_page=True)
        b.close()
    print("OVERALL", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
