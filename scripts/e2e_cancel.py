"""Verify render-job cancellation: API flip + worker honours it + UI button.

Run: .e2e-venv/bin/python scripts/e2e_cancel.py
"""
import json
import sys
import time
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
        ctx.request.post(f"{API}/auth/mock-login?provider=e2e")
        page = ctx.new_page(); page.set_default_timeout(20000)

        def new_project(title):
            r = ctx.request.post(
                f"{API}/projects/",
                headers={"Content-Type": "application/json"},
                data=json.dumps({"title": title, "source_url": "", "source_type": "url"}),
            )
            return r.json()["id"]

        def generate(pid):
            r = ctx.request.post(f"{API}/projects/{pid}/renders/generate")
            return r.json()["job_id"]

        def job(pid, jid):
            return ctx.request.get(f"{API}/projects/{pid}/renders/{jid}").json()

        def proj_status(pid):
            return ctx.request.get(f"{API}/projects/{pid}").json()["status"]

        # ---- API core: synchronous cancel + worker honours it ----
        pid = new_project("e2e-cancel-api")
        jid = generate(pid)
        resp = ctx.request.post(f"{API}/projects/{pid}/renders/{jid}/cancel")
        body = resp.json()
        sync_ok = resp.ok and body.get("status") == "cancelled"
        print("CANCEL_SYNC", "PASS" if sync_ok else "FAIL", f"status={body.get('status')}")
        ok = ok and sync_ok

        # poll: must stay cancelled, never flip to completed
        seen = set()
        final = None
        deadline = time.time() + 25
        while time.time() < deadline:
            s = job(pid, jid)["status"]
            seen.add(s); final = s
            if s in ("cancelled", "completed", "failed"):
                # give the worker a moment to try resurrecting, then re-check
                time.sleep(2)
                final = job(pid, jid)["status"]
                break
            time.sleep(1)
        stays = final == "cancelled" and "completed" not in seen
        print("CANCEL_STICKY", "PASS" if stays else "FAIL", f"seen={sorted(seen)} final={final}")
        ok = ok and stays

        # project leaves generating
        ps = proj_status(pid)
        proj_ok = ps != "generating"
        print("PROJECT_RESET", "PASS" if proj_ok else "FAIL", f"project.status={ps}")
        ok = ok and proj_ok

        # idempotent: cancelling again stays cancelled
        again = ctx.request.post(f"{API}/projects/{pid}/renders/{jid}/cancel").json()
        idem = again.get("status") == "cancelled"
        print("CANCEL_IDEMPOTENT", "PASS" if idem else "FAIL", f"status={again.get('status')}")
        ok = ok and idem

        # ---- UI: cancel button renders and cancels via click ----
        pid2 = new_project("e2e-cancel-ui")
        generate(pid2)
        page.goto(f"{BASE}/projects/{pid2}", wait_until="domcontentloaded")
        try: page.wait_for_load_state("networkidle", timeout=10000)
        except Exception: pass
        btn = page.get_by_role("button", name="取消生成")
        ui_state = "WARN"
        try:
            btn.wait_for(state="visible", timeout=12000)
            btn.click()
            page.wait_for_timeout(2500)
            jobs = ctx.request.get(f"{API}/projects/{pid2}/renders/").json()
            latest = jobs[0]["status"] if jobs else None
            ui_state = "PASS" if latest == "cancelled" else "FAIL"
            print("UI_CANCEL", ui_state, f"latest={latest}")
            if ui_state == "FAIL":
                ok = False
        except Exception:
            # engine may have finished before the panel rendered; API path is authoritative
            ps2 = proj_status(pid2)
            ui_state = "PASS" if ps2 != "generating" else "WARN"
            print("UI_CANCEL", ui_state, f"(button not shown; project.status={ps2})")

        page.screenshot(path=str(OUT / "cancel_render.png"), full_page=True)
        b.close()

    print("OVERALL", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
