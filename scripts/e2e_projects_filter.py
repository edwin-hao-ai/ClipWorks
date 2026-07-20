"""Verify the projects list search + status filter.

Run: .e2e-venv/bin/python scripts/e2e_projects_filter.py
"""
import json
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
API = "http://localhost:8000"
OUT = Path("/Users/edwinhao/ClipWorks/data/e2e_audit")
TAG = f"e2e-filter-{int(time.time())}"


def main():
    ok = True
    created = []
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        ctx.request.post(f"{API}/auth/mock-login?provider=google")
        page = ctx.new_page(); page.set_default_timeout(20000)

        def create(title):
            r = ctx.request.post(
                f"{API}/projects/",
                headers={"Content-Type": "application/json"},
                data=json.dumps({"title": title, "source_url": "", "source_type": "url"}),
            )
            pid = r.json()["id"]
            created.append(pid)
            return pid

        title_a = f"{TAG}-apple"
        title_b = f"{TAG}-banana"
        create(title_a); create(title_b)

        def cards():
            return page.get_by_test_id("project-card")

        page.goto(f"{BASE}/projects", wait_until="domcontentloaded")
        try: page.wait_for_load_state("networkidle", timeout=10000)
        except Exception: pass
        page.get_by_test_id("project-search").wait_for(state="visible", timeout=12000)

        search = page.get_by_test_id("project-search")

        # exact substring -> only the apple project
        search.fill(f"{TAG}-apple"); page.wait_for_timeout(400)
        n_apple = cards().count()
        apple_ok = n_apple == 1
        print("SEARCH_SUBSTRING", "PASS" if apple_ok else "FAIL", f"cards={n_apple} want 1")
        ok = ok and apple_ok

        # shared tag -> both projects
        search.fill(TAG); page.wait_for_timeout(400)
        n_both = cards().count()
        both_ok = n_both == 2
        print("SEARCH_BOTH", "PASS" if both_ok else "FAIL", f"cards={n_both} want 2")
        ok = ok and both_ok

        # both are 'draft' -> filtering to 'ready' yields 0 with empty state
        page.get_by_test_id("status-filter-ready").click(); page.wait_for_timeout(400)
        n_ready = cards().count()
        empty_visible = page.get_by_text("没有匹配的项目").is_visible()
        ready_ok = n_ready == 0 and empty_visible
        print("FILTER_READY_EMPTY", "PASS" if ready_ok else "FAIL",
              f"cards={n_ready} empty={empty_visible}")
        ok = ok and ready_ok

        # back to 'draft' -> both again
        page.get_by_test_id("status-filter-draft").click(); page.wait_for_timeout(400)
        n_draft = cards().count()
        draft_ok = n_draft == 2
        print("FILTER_DRAFT_BOTH", "PASS" if draft_ok else "FAIL", f"cards={n_draft} want 2")
        ok = ok and draft_ok

        page.screenshot(path=str(OUT / "projects_filter.png"), full_page=True)

        # cleanup to avoid further polluting the projects list
        for pid in created:
            try: ctx.request.delete(f"{API}/projects/{pid}")
            except Exception: pass

        b.close()
    print("OVERALL", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
