"""Verify the billing page plan switcher persists the selected plan.

Run: .e2e-venv/bin/python scripts/e2e_billing_plan.py
"""
import json
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
API = "http://localhost:8000"
OUT = Path("/Users/edwinhao/ClipWorks/data/e2e_audit")
LABEL = {"free": "免费版", "pro": "专业版", "enterprise": "企业版"}


def main():
    ok = True
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        ctx.request.post(f"{API}/auth/mock-login?provider=google")
        page = ctx.new_page(); page.set_default_timeout(20000)

        def stats():
            return ctx.request.get(f"{API}/auth/me/stats").json()

        plan0 = stats()["current_plan"]
        target = "pro" if plan0 == "free" else "free"

        # invalid plan is rejected by the schema (422)
        bad = ctx.request.put(
            f"{API}/auth/me",
            headers={"Content-Type": "application/json"},
            data=json.dumps({"plan": "bogus"}),
        )
        invalid_ok = bad.status == 422
        print("INVALID_PLAN_REJECTED", "PASS" if invalid_ok else "FAIL", f"status={bad.status}")
        ok = ok and invalid_ok

        page.goto(f"{BASE}/billing", wait_until="domcontentloaded")
        try: page.wait_for_load_state("networkidle", timeout=10000)
        except Exception: pass
        page.get_by_test_id("stat-plan").wait_for(state="visible", timeout=12000)

        page.get_by_test_id(f"plan-select-{target}").click()
        # wait until the API reflects the new plan
        deadline = time.time() + 12
        cur = plan0
        while time.time() < deadline:
            cur = stats()["current_plan"]
            if cur == target:
                break
            time.sleep(0.5)
        switched = cur == target
        print("PLAN_SWITCH_API", "PASS" if switched else "FAIL", f"{plan0}->{cur} want {target}")
        ok = ok and switched

        # the now-current plan button is disabled and labelled as in-use
        page.wait_for_timeout(600)
        cur_btn = page.get_by_test_id(f"plan-select-{target}")
        disabled = cur_btn.is_disabled()
        stat_text = page.get_by_test_id("stat-plan").inner_text().strip()
        ui_ok = disabled and stat_text == LABEL[target]
        print("PLAN_SWITCH_UI", "PASS" if ui_ok else "FAIL",
              f"disabled={disabled} stat_plan={stat_text!r} want {LABEL[target]!r}")
        ok = ok and ui_ok

        page.screenshot(path=str(OUT / "billing_plan.png"), full_page=True)

        # restore original plan (best-effort) so we leave the demo user untouched
        if plan0 != target:
            page.get_by_test_id(f"plan-select-{plan0}").click()
            deadline = time.time() + 12
            back = cur
            while time.time() < deadline:
                back = stats()["current_plan"]
                if back == plan0:
                    break
                time.sleep(0.5)
            restored = back == plan0
            print("PLAN_RESTORE", "PASS" if restored else "FAIL", f"back={back} want {plan0}")
            ok = ok and restored

        b.close()
    print("OVERALL", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
