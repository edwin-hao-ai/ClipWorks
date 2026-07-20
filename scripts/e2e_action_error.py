"""Verify a failed workspace ACTION shows an inline error banner, not the full-screen error page.

Previously any setError() during a ready workspace (save/apply/re-render) tripped the
`if (error || !project)` guard and replaced the entire timeline with a full-page
"重试" screen. Now action errors render as a dismissible inline banner and the
workspace stays usable.

Uses a ready demo@google project (abundant residue) and route-mocks the re-render
POST to a 500 so the server-side 0-credit gate never fires and no real render runs.

Run: .e2e-venv/bin/python scripts/e2e_action_error.py
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
        page = ctx.new_page(); page.set_default_timeout(25000)

        # find an existing ready project with a completed job (rerender button visible)
        pid = None
        for proj in ctx.request.get(f"{API}/projects/").json():
            if proj.get("status") != "ready":
                continue
            jobs = ctx.request.get(f"{API}/projects/{proj['id']}/renders/").json()
            if isinstance(jobs, list) and jobs and jobs[0]["status"] == "completed" and jobs[0].get("output_url"):
                pid = proj["id"]; break
        if not pid:
            print("SETUP", "WARN", "no ready demo@google project; skipping")
            b.close(); sys.exit(0)
        print("SETUP", "PASS", f"project={pid[:8]}")

        # force the re-render request to fail with a NON-402 error in the browser,
        # bypassing the server-side credit gate so we exercise the generic banner.
        page.route("**/renders/generate", lambda route: route.fulfill(status=500, body="boom"))
        page.goto(f"{BASE}/projects/{pid}", wait_until="domcontentloaded")
        try: page.wait_for_load_state("networkidle", timeout=10000)
        except Exception: pass
        page.wait_for_timeout(2500)

        btn = page.get_by_role("button", name="用当前时间线重新渲染")
        try:
            btn.wait_for(state="visible", timeout=15000)
        except Exception:
            page.screenshot(path=str(OUT / "action_error_no_button.png"), full_page=True)
            print("RERENDER_BUTTON", "FAIL", "re-render button not visible")
            b.close(); sys.exit(1)
        btn.click()
        page.wait_for_timeout(2500)
        page.screenshot(path=str(OUT / "action_error_banner.png"), full_page=True)

        banner = page.get_by_test_id("action-error-banner")
        banner_visible = banner.is_visible()
        banner_txt = banner.inner_text() if banner_visible else ""
        banner_ok = banner_visible and "500" in banner_txt
        print("INLINE_ERROR_BANNER", "PASS" if banner_ok else "FAIL", banner_txt[:80])
        ok = ok and banner_ok

        still_here = page.get_by_role("button", name="用当前时间线重新渲染").is_visible()
        fullscreen = page.get_by_role("button", name="重试").is_visible()
        intact = still_here and not fullscreen
        print("WORKSPACE_INTACT", "PASS" if intact else "FAIL",
              f"rerender_visible={still_here} fullscreen_retry={fullscreen}")
        ok = ok and intact

        if banner_visible:
            page.get_by_role("button", name="关闭错误提示").click()
            page.wait_for_timeout(500)
            dismissed = not page.get_by_test_id("action-error-banner").is_visible()
            print("DISMISS_BANNER", "PASS" if dismissed else "FAIL")
            ok = ok and dismissed

        b.close()

    print("OVERALL", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
