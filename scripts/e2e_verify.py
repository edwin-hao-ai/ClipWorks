"""Targeted re-verification for the critical/ambiguous E2E findings.

Fixes selector issues from the broad audit and produces solid evidence for:
  A) home create flow (correct placeholder selector)
  B) LaunchNav 素材库 -> /projects/demo/assets truly broken (API 403/404)
  C) editor Save is a no-op for edits (Timeline has no onChange) + Save PUT works
  D) assets upload (first file input)
  E) planning stream on a FRESH project (does it produce a plan or fail?)

Run: .e2e-venv/bin/python scripts/e2e_verify.py
"""

import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
API = "http://localhost:8000"
OUT = Path("/Users/edwinhao/ClipWorks/data/e2e_audit")
OUT.mkdir(parents=True, exist_ok=True)
R = []


def rec(n, s, d=""):
    R.append({"name": n, "status": s, "detail": d})
    print(f"[{s:5}] {n} :: {d}")


def main():
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        # login via API (reliable)
        ctx.request.post(f"{API}/auth/mock-login?provider=google")
        page = ctx.new_page()
        page.set_default_timeout(15000)

        # --- A: home create ---
        page.goto(f"{BASE}/", wait_until="domcontentloaded")
        page.wait_for_load_state("networkidle", timeout=10000).ok if False else None
        try:
            page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
        try:
            box = page.locator('input[placeholder^="例如"]').first
            box.wait_for(state="visible", timeout=8000)
            box.fill("E2E 验证项目 15 秒 9:16 产品发布会风格活泼")
            page.get_by_role("button", name="开始创作").click()
            page.wait_for_url(lambda u: "/projects/" in u and u.rstrip("/") != BASE + "/projects", timeout=25000)
            pid = page.url.rstrip("/").split("/projects/")[-1].split("?")[0]
            rec("A home create project", "PASS", f"-> {pid}")
            page.screenshot(path=str(OUT / "v_A_workspace.png"), full_page=True)
        except Exception as e:
            rec("A home create project", "FAIL", str(e)[:200])
            pid = None

        # --- B: 素材库 link truly broken ---
        page.goto(f"{BASE}/", wait_until="domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
        api_demo = ctx.request.get(f"{API}/projects/demo")
        rec("B GET /projects/demo", "INFO", f"status={api_demo.status} (proves hardcoded demo id is invalid)")
        try:
            page.get_by_role("link", name="素材库").click()
            try:
                page.wait_for_url("**/projects/**", timeout=8000)
            except Exception:
                pass
            page.wait_for_timeout(1500)
            page.screenshot(path=str(OUT / "v_B_assets_demo.png"), full_page=True)
            rec("B 素材库 navigation", "FAIL" if "demo" in page.url else "WARN",
                f"landed url={page.url}; body~={page.inner_text('body')[:120]!r}")
        except Exception as e:
            rec("B 素材库 navigation", "FAIL", str(e)[:200])

        # pick a project for C/D (use freshly created, else first existing)
        if not pid:
            lst = ctx.request.get(f"{API}/projects/").json()
            pid = lst[0]["id"] if lst else None

        # --- C: editor save no-op ---
        if pid:
            page.goto(f"{BASE}/projects/{pid}/editor", wait_until="domcontentloaded")
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass
            page.wait_for_timeout(1500)
            page.screenshot(path=str(OUT / "v_C_editor.png"), full_page=True)
            before = json.dumps(ctx.request.get(f"{API}/compositions/{pid}").json(), sort_keys=True)
            try:
                page.get_by_role("button", name="保存").click()
                page.wait_for_timeout(1500)
                after = json.dumps(ctx.request.get(f"{API}/compositions/{pid}").json(), sort_keys=True)
                saved = "已保存" in page.inner_text("body")
                rec("C editor Save", "PASS" if saved else "WARN",
                    f"已保存 shown={saved}; composition identical after save={before == after} (no editable state lifted)")
            except Exception as e:
                rec("C editor Save", "FAIL", str(e)[:200])
            # zoom buttons present?
            body = page.inner_text("body")
            rec("C editor zoom/trim/split UI", "INFO",
                "no trim/split/drag handles exist (static code: ClipBlock has only onClick, Timeline has no onChange prop)")

        # --- D: assets upload (first input) ---
        if pid:
            page.goto(f"{BASE}/projects/{pid}/assets", wait_until="domcontentloaded")
            try:
                page.wait_for_load_state("networkidle", timeout=10000)
            except Exception:
                pass
            page.wait_for_timeout(1200)
            before = ctx.request.get(f"{API}/projects/{pid}/assets/").json()
            bn = len(before) if isinstance(before, list) else 0
            try:
                page.locator("input[type=file]").first.set_input_files(str(OUT / "tiny.png"))
                page.wait_for_timeout(3000)
                after = ctx.request.get(f"{API}/projects/{pid}/assets/").json()
                an = len(after) if isinstance(after, list) else 0
                page.screenshot(path=str(OUT / "v_D_assets.png"), full_page=True)
                rec("D assets upload", "PASS" if an > bn else "FAIL", f"{bn} -> {an}")
            except Exception as e:
                rec("D assets upload", "FAIL", str(e)[:200])

        # --- E: planning stream on a FRESH project ---
        fresh = ctx.request.post(f"{API}/projects/", data=json.dumps({
            "title": "E2E 规划验证", "source_url": "", "source_type": "url",
            "target_format": "9:16", "target_duration": 15,
        })).json()
        fpid = fresh["id"]
        page.goto(f"{BASE}/projects/{fpid}", wait_until="domcontentloaded")
        try:
            page.wait_for_load_state("networkidle", timeout=10000)
        except Exception:
            pass
        page.wait_for_timeout(2000)
        try:
            ta = page.locator("textarea").first
            ta.wait_for(state="visible", timeout=8000)
            ta.fill("请规划 4 个镜头，15 秒，9:16，活泼风格的产品介绍")
            # find the send button: the button adjacent to the textarea (type submit or last button in form)
            ta.press("Enter")
            deadline = time.time() + 60
            outcome = "timeout"
            while time.time() < deadline:
                txt = page.inner_text("body")
                if "确认生成" in txt:
                    outcome = "plan_ready_approve_visible"
                    break
                if "响应失败" in txt or "Agent 响应失败" in txt:
                    outcome = "agent_failed_no_fallback"
                    break
                page.wait_for_timeout(1500)
            page.screenshot(path=str(OUT / "v_E_planning.png"), full_page=True)
            rec("E planning stream (fresh project)",
                "PASS" if outcome == "plan_ready_approve_visible" else ("FAIL" if outcome == "agent_failed_no_fallback" else "WARN"),
                f"outcome={outcome} after 60s")
        except Exception as e:
            rec("E planning stream (fresh project)", "FAIL", str(e)[:200])

        (OUT / "verify.json").write_text(json.dumps(R, ensure_ascii=False, indent=2))
        from collections import Counter
        print("\n=== TALLY ===", dict(Counter(r["status"] for r in R)))
        b.close()


if __name__ == "__main__":
    main()
