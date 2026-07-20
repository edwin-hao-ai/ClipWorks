"""Verify the 0-credit hard gate.

The demo@google account is permanently at 0 credits (well over its quota). Every
render-triggering endpoint must now refuse with HTTP 402 instead of queueing a
job, and the workspace must surface an inline upgrade banner rather than the
full-screen error page.

Run: .e2e-venv/bin/python scripts/e2e_credit_gate.py
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
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        ctx.request.post(f"{API}/auth/mock-login?provider=google")
        page = ctx.new_page(); page.set_default_timeout(25000)

        # confirm the account really is depleted, otherwise the gate test is meaningless
        stats = ctx.request.get(f"{API}/auth/me/stats").json()
        credits = stats.get("remaining_credits")
        depleted = credits == 0
        print("ACCOUNT_DEPLETED", "PASS" if depleted else "FAIL", f"credits={credits}")
        ok = ok and depleted

        def new_project(title):
            r = ctx.request.post(
                f"{API}/projects/",
                headers={"Content-Type": "application/json"},
                data=json.dumps({"title": title, "source_url": "", "source_type": "url"}),
            )
            return r.json()["id"]

        # 1) /renders/generate must 402
        pid = new_project("e2e-credit-gate-generate")
        r1 = ctx.request.post(f"{API}/projects/{pid}/renders/generate")
        g1 = r1.status == 402 and "额度不足" in r1.text()
        print("GATE_GENERATE", "PASS" if g1 else "FAIL", f"status={r1.status} body={r1.text()[:120]}")
        ok = ok and g1

        # 2) /agent/chat with render=true must 402
        r2 = ctx.request.post(
            f"{API}/projects/{pid}/agent/chat",
            headers={"Content-Type": "application/json"},
            data=json.dumps({"message": "把标题改成红色", "render": True}),
        )
        g2 = r2.status == 402 and "额度不足" in r2.text()
        print("GATE_AGENT_CHAT", "PASS" if g2 else "FAIL", f"status={r2.status} body={r2.text()[:120]}")
        ok = ok and g2

        # 3) no render job should have been created for the rejected requests
        jobs = ctx.request.get(f"{API}/projects/{pid}/renders/").json()
        no_job = len(jobs) == 0
        print("GATE_NO_JOB_QUEUED", "PASS" if no_job else "FAIL", f"jobs={len(jobs)}")
        ok = ok and no_job

        # 4) UI: an existing ready project shows the soft banner; clicking
        #    re-render turns it into the hard "已被拦截" banner (creditBlocked).
        ready_pid = None
        for proj in ctx.request.get(f"{API}/projects/").json():
            if proj.get("status") != "ready":
                continue
            pj = ctx.request.get(f"{API}/projects/{proj['id']}/renders/").json()
            if isinstance(pj, list) and pj and pj[0]["status"] == "completed" and pj[0].get("output_url"):
                ready_pid = proj["id"]; break

        if not ready_pid:
            print("UI_GATE_BANNER", "WARN", "no ready demo@google project to exercise the UI")
        else:
            page.goto(f"{BASE}/projects/{ready_pid}", wait_until="domcontentloaded")
            try: page.wait_for_load_state("networkidle", timeout=10000)
            except Exception: pass
            banner = page.get_by_test_id("credits-depleted-banner")
            try:
                banner.wait_for(state="visible", timeout=12000)
                soft = banner.inner_text()
                soft_ok = "额度为 0" in soft
                print("UI_SOFT_BANNER", "PASS" if soft_ok else "FAIL", soft[:60])
                ok = ok and soft_ok

                page.get_by_role("button", name="用当前时间线重新渲染").click()
                page.wait_for_timeout(2500)
                hard = banner.inner_text()
                hard_ok = "已被拦截" in hard and "计费页" in hard
                print("UI_HARD_BANNER", "PASS" if hard_ok else "FAIL", hard[:80])
                ok = ok and hard_ok
                # workspace must still be visible (no full-screen error takeover)
                still_here = page.get_by_role("button", name="用当前时间线重新渲染").is_visible()
                print("UI_WORKSPACE_INTACT", "PASS" if still_here else "FAIL")
                ok = ok and still_here
            except Exception as exc:
                print("UI_GATE_BANNER", "FAIL", repr(exc))
                ok = False
            page.screenshot(path=str(OUT / "credit_gate.png"), full_page=True)

        b.close()

    print("OVERALL", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
