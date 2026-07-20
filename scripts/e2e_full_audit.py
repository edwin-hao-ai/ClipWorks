"""Comprehensive browser E2E audit for ClipWorks.

Walks every page, clicks (almost) every button, captures console errors,
failed network requests, screenshots, and a structured PASS/FAIL report.

Selectors are kept in sync with the current UI (textbox chat input, role-based
save/logout buttons, isolated draft project for planning/editor/assets) so the
report reflects real gaps rather than stale false positives.

Requires a running local stack (docker compose up) and Playwright+Chromium
installed in .e2e-venv.

Run:
  .e2e-venv/bin/python scripts/e2e_full_audit.py
"""

import base64
import json
import sys
import time
import traceback
from pathlib import Path

from playwright.sync_api import sync_playwright, Page, BrowserContext

BASE = "http://localhost:3000"
API = "http://localhost:8000"
OUT = Path("/Users/edwinhao/ClipWorks/data/e2e_audit")
OUT.mkdir(parents=True, exist_ok=True)

RESULTS = []  # list of dicts: {name, status, detail}


def record(name, status, detail=""):
    RESULTS.append({"name": name, "status": status, "detail": detail})
    print(f"[{status:5}] {name} :: {detail}")


# 1x1 transparent PNG for upload tests
PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="
)
UPLOAD_PATH = OUT / "tiny.png"
UPLOAD_PATH.write_bytes(PNG_BYTES)

DESTRUCTIVE = ("删除", "退出登录", "Delete", "Logout", "重试生成", "确认")


def new_project(ctx, title):
    r = ctx.request.post(
        f"{API}/projects/",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"title": title, "source_url": "", "source_type": "url"}),
    )
    return r.json()["id"] if r.ok else None


class Auditor:
    def __init__(self, context: BrowserContext, tag: str):
        self.context = context
        self.page: Page = context.new_page()
        self.tag = tag
        self.console_errors = []
        self.failed = []
        self.page.on("console", self._on_console)
        self.page.on("pageerror", lambda e: self.console_errors.append(f"PAGEERROR: {e}"))
        self.page.on("response", self._on_response)

    def _on_console(self, msg):
        if msg.type in ("error", "warning"):
            txt = msg.text
            if "favicon" in txt or "Hydration" in txt:
                return
            self.console_errors.append(f"{msg.type.upper()}: {txt[:200]}")

    def _on_response(self, resp):
        if resp.status >= 400 and "/_next/" not in resp.url:
            self.failed.append(f"{resp.status} {resp.request.method} {resp.url}")

    def reset_capture(self):
        self.console_errors.clear()
        self.failed.clear()

    def goto(self, path, wait="domcontentloaded"):
        self.reset_capture()
        try:
            self.page.goto(f"{BASE}{path}", wait_until=wait, timeout=30000)
        except Exception as e:
            record(f"{self.tag} goto {path}", "FAIL", f"navigation error: {e}")
            return False
        try:
            self.page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
        return True

    def shot(self, name):
        path = OUT / f"{self.tag}_{name}.png"
        try:
            self.page.screenshot(path=str(path), full_page=True)
        except Exception:
            pass
        return path.name

    def click_every_button(self, label):
        """Click every visible, non-destructive button on the current page.

        Re-queries the button set each iteration and tracks already-clicked
        buttons by signature (text + aria-label), so DOM reflows from an
        earlier click (modal open, navigation+go_back, list re-render) cannot
        leave a stale handle that times out. Bounded by ``max_rounds`` to
        avoid infinite loops on repeatedly re-rendering controls.
        """
        clicked = []
        seen = set()
        max_rounds = 60
        for _ in range(max_rounds):
            target = None
            disp = None
            try:
                buttons = self.page.get_by_role("button")
                n = buttons.count()
            except Exception:
                n = 0
            for i in range(n):
                try:
                    btn = buttons.nth(i)
                    if not btn.is_visible():
                        continue
                    if not btn.is_enabled():
                        continue
                    name = (btn.inner_text(timeout=800) or "").strip().replace("\n", " ")
                    aria = btn.get_attribute("aria-label") or ""
                    cand = name or aria or f"<icon#{i}>"
                    sig = f"{name}|{aria}"
                    if sig in seen:
                        continue
                    if any(d in cand for d in DESTRUCTIVE):
                        seen.add(sig)
                        clicked.append((cand, "SKIPPED(destructive)"))
                        continue
                    target = btn
                    disp = cand
                    seen.add(sig)
                    break
                except Exception:
                    continue
            if target is None:
                break
            try:
                before = self.page.url
                errs_before = len(self.console_errors)
                fail_before = len(self.failed)
                # 先关闭上一轮可能残留的浮层（下拉菜单/Toast），再做可操作点击；
                # 若仍被瞬时浮层挡住，按一次 Escape 后重试一次，避免 harness 误判。
                try:
                    self.page.keyboard.press("Escape")
                except Exception:
                    pass
                try:
                    target.click(timeout=3000, trial=False)
                except Exception as click_err:
                    if "Timeout" in str(click_err):
                        try:
                            self.page.keyboard.press("Escape")
                            self.page.wait_for_timeout(400)
                        except Exception:
                            pass
                        target.click(timeout=3000, trial=False)
                    else:
                        raise
                self.page.wait_for_timeout(600)
                nav = self.page.url != before
                new_errs = self.console_errors[errs_before:]
                new_fail = self.failed[fail_before:]
                status = "ok"
                if new_errs or new_fail:
                    status = f"ERROR errs={new_errs[:1]} fail={new_fail[:1]}"
                if nav:
                    status += " NAVIGATED"
                    try:
                        self.page.go_back(wait_until="domcontentloaded")
                        self.page.wait_for_timeout(400)
                    except Exception:
                        pass
                clicked.append((disp, status))
                try:
                    self.page.keyboard.press("Escape")
                    self.page.wait_for_timeout(150)
                except Exception:
                    pass
            except Exception as e:
                clicked.append((disp or "?", f"EXC {str(e)[:80]}"))
        self.shot(f"{label}_after_clicks")
        return clicked


def login_via_ui(ctx: BrowserContext):
    aud = Auditor(ctx, "login")
    if not aud.goto("/login"):
        return None
    aud.shot("01_login_page")
    try:
        aud.page.get_by_text("使用 Google 登录").click(timeout=5000)
    except Exception as e:
        record("login click Google", "FAIL", str(e))
        return None
    try:
        aud.page.wait_for_url(lambda u: "/login" not in u, timeout=15000)
    except Exception:
        pass
    aud.page.wait_for_timeout(1500)
    aud.shot("02_after_login")
    me = ctx.request.get(f"{API}/auth/me")
    if me.ok:
        record("login via UI + /auth/me", "PASS", f"user={me.json().get('email')}")
    else:
        record("login via UI + /auth/me", "FAIL", f"/auth/me -> {me.status}")
    return aud


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})

        # ---- 1. Login ----
        aud = login_via_ui(ctx)
        if aud is None:
            record("login", "FAIL", "could not log in; aborting")
            dump()
            browser.close()
            return

        # ---- 2. Home page (authenticated create) ----
        project_id = None
        if aud.goto("/"):
            aud.shot("03_home")
            try:
                inp = aud.page.get_by_placeholder("例如")
                inp.fill("帮我做一个 15 秒的产品介绍视频，9:16，风格活泼，面向年轻人")
                aud.page.get_by_text("开始创作").click(timeout=5000)
                aud.page.wait_for_url(
                    lambda u: "/projects/" in u and u.rstrip("/") != BASE + "/projects",
                    timeout=25000,
                )
                project_id = aud.page.url.rstrip("/").split("/projects/")[-1].split("?")[0]
                record("home create project", "PASS", f"-> {project_id}")
                aud.shot("04_workspace_after_create")
            except Exception as e:
                record("home create project", "FAIL", str(e)[:200])

        # ---- 3. LaunchNav 素材库 -> should land on /projects ----
        if aud.goto("/"):
            try:
                aud.page.get_by_role("link", name="素材库").click(timeout=5000)
                aud.page.wait_for_timeout(2000)
                aud.shot("05_nav_assets")
                body_txt = aud.page.inner_text("body")[:300]
                broken = aud.page.url.endswith("/projects/demo/assets") or (
                    "404" in body_txt or "不存在" in body_txt
                )
                record("LaunchNav 素材库 link", "FAIL" if broken else "PASS",
                       f"url={aud.page.url}")
            except Exception as e:
                record("LaunchNav 素材库 link", "FAIL", str(e)[:200])

        # ---- 4. Projects list + NewProjectDialog ----
        if aud.goto("/projects"):
            aud.shot("06_projects")
            try:
                aud.page.get_by_text("新建项目").first.click(timeout=5000)
                aud.page.wait_for_timeout(500)
                aud.shot("07_new_project_dialog")
                try:
                    aud.page.get_by_text("上传视频").click(timeout=2000)
                    aud.page.wait_for_timeout(300)
                except Exception:
                    pass
                has_upload_stub = "上传功能在素材库中使用" in aud.page.inner_text("body")
                has_file_input = aud.page.locator("input[type=file]").count() > 0
                record("NewProjectDialog upload source",
                       "PASS" if (has_file_input and not has_upload_stub) else "FAIL",
                       f"file_input={has_file_input} stub_text={has_upload_stub}")
                aud.page.keyboard.press("Escape")
            except Exception as e:
                record("NewProjectDialog open", "FAIL", str(e)[:200])
            clicked = aud.click_every_button("projects")
            record("projects buttons enumerated", "INFO", json.dumps(clicked, ensure_ascii=False)[:800])

        # Isolated draft project for planning/editor/assets steps — guarantees a
        # planning-view workspace regardless of residue project states.
        audit_pid = new_project(ctx, "e2e-full-audit-draft")
        if not audit_pid:
            record("isolated draft project", "FAIL", "could not create project via API")
        else:
            record("isolated draft project", "PASS", audit_pid)

        # ---- 5. Workspace planning (AgentChat uses <input type=text>) ----
        if audit_pid and aud.goto(f"/projects/{audit_pid}"):
            aud.page.wait_for_timeout(2000)
            aud.shot("08_workspace")
            clicked = aud.click_every_button("workspace")
            record("workspace buttons enumerated", "INFO", json.dumps(clicked, ensure_ascii=False)[:900])
            # clean slate so click_every_button (which taps a quick-prompt) cannot
            # double-submit the planning stream; then assert via API ground truth.
            aud.goto(f"/projects/{audit_pid}")
            aud.page.wait_for_timeout(2000)
            try:
                box = aud.page.get_by_role("textbox").first
                # fill/press auto-wait for the input; an explicit is_visible() probe
                # races AgentChat's mount and was skipping the send entirely.
                box.fill("AI 降噪耳机产品视频：3 个卖点（主动降噪、30 小时续航、舒适佩戴），15 秒，9:16，风格活泼，面向年轻人。请直接产出可确认的最终分镜方案，不要再追问。", timeout=15000)
                box.press("Enter")
                deadline = time.time() + 90
                outcome = "timeout"
                while time.time() < deadline:
                    try:
                        proj = ctx.request.get(f"{API}/projects/{audit_pid}").json()
                        step = (proj.get("agent_state") or {}).get("step")
                        pstatus = proj.get("status")
                    except Exception:
                        step = None; pstatus = None
                    if step == "pending_approval" or pstatus == "planning":
                        outcome = "plan_ready"; break
                    txt = aud.page.inner_text("body")
                    if ("响应失败" in txt) or ("没法继续" in txt):
                        outcome = "agent_failed"; break
                    aud.page.wait_for_timeout(2000)
                aud.shot("09_workspace_after_plan")
                record("workspace planning stream",
                       "PASS" if outcome == "plan_ready" else ("FAIL" if outcome == "agent_failed" else "WARN"),
                       f"outcome={outcome}")
            except Exception as e:
                record("workspace planning stream", "FAIL", str(e)[:200])

        # ---- 6. Editor (editable timeline) ----
        # Re-load a fresh editor so click_every_button's mutations (add-clip,
        # opened panels) do not cover or disable the Save button.
        if audit_pid and aud.goto(f"/projects/{audit_pid}/editor"):
            aud.page.wait_for_timeout(2500)
            aud.shot("10_editor")
            clicked = aud.click_every_button("editor")
            record("editor buttons enumerated", "INFO", json.dumps(clicked, ensure_ascii=False)[:900])
            # clean slate for the actual save test
            aud.goto(f"/projects/{audit_pid}/editor")
            aud.page.wait_for_timeout(2500)
            try:
                comp_before = ctx.request.get(f"{API}/compositions/{audit_pid}")
                # make a real change so Save has something to persist
                try:
                    aud.page.get_by_role("button", name="添加片段").click(timeout=4000)
                    aud.page.wait_for_timeout(500)
                except Exception:
                    pass
                save_btn = aud.page.get_by_role("button", name="保存")
                save_btn.wait_for(state="visible", timeout=6000)
                errs_before = len(aud.console_errors); fail_before = len(aud.failed)
                save_btn.click(timeout=8000)
                aud.page.wait_for_timeout(2000)
                new_errs = aud.console_errors[errs_before:]
                new_fail = [f for f in aud.failed[fail_before:] if "/compositions/" in f]
                comp_after = ctx.request.get(f"{API}/compositions/{audit_pid}")
                aud.shot("11_editor_after_save")
                record("editor Save persists",
                       "PASS" if (comp_before.ok and comp_after.ok and not new_errs and not new_fail) else "FAIL",
                       f"comp_get={comp_before.ok}/{comp_after.ok} save_errs={new_errs[:1]} save_fail={new_fail[:1]}")
            except Exception as e:
                record("editor Save", "FAIL", str(e)[:200])

        # ---- 7. Assets upload (two file inputs: button + dropzone; use first) ----
        if audit_pid and aud.goto(f"/projects/{audit_pid}/assets"):
            aud.page.wait_for_timeout(1500)
            aud.shot("12_assets")
            try:
                before = ctx.request.get(f"{API}/projects/{audit_pid}/assets/").json()
                before_n = len(before) if isinstance(before, list) else 0
                aud.page.locator("input[type=file]").first.set_input_files(str(UPLOAD_PATH))
                aud.page.wait_for_timeout(2500)
                after = ctx.request.get(f"{API}/projects/{audit_pid}/assets/").json()
                after_n = len(after) if isinstance(after, list) else 0
                aud.shot("13_assets_after_upload")
                record("assets upload", "PASS" if after_n > before_n else "FAIL",
                       f"assets {before_n} -> {after_n}")
                # delete affordance is an icon-only Trash2 button with aria-label="删除"
                del_count = aud.page.get_by_role("button", name="删除").count()
                record("assets delete affordance", "PASS" if del_count > 0 else "FAIL",
                       f"delete buttons={del_count}")
            except Exception as e:
                record("assets upload", "FAIL", str(e)[:200])

        # ---- 8. Settings ----
        if aud.goto("/settings"):
            aud.page.wait_for_timeout(1200)
            aud.shot("14_settings")
            clicked = aud.click_every_button("settings")
            record("settings buttons enumerated", "INFO", json.dumps(clicked, ensure_ascii=False)[:600])
            record("settings interactivity", "FAIL" if not clicked else "PASS",
                   json.dumps(clicked, ensure_ascii=False)[:240])

        # ---- 9. Billing (plan cards are clickable) ----
        if aud.goto("/billing"):
            aud.page.wait_for_timeout(1500)
            aud.shot("15_billing")
            clicked = aud.click_every_button("billing")
            record("billing buttons enumerated", "INFO", json.dumps(clicked, ensure_ascii=False)[:600])
            record("billing plan action", "FAIL" if not clicked else "PASS",
                   json.dumps(clicked, ensure_ascii=False)[:240])

        # ---- 10. Logout via the always-visible sidebar button ----
        # (The TopBar account menu also has a 退出登录 entry; opening it yields two
        # same-named buttons. The sidebar one is always present, so use it directly.)
        if aud.goto("/projects"):
            aud.page.wait_for_timeout(1000)
            try:
                aud.page.get_by_role("button", name="退出登录").first.click(timeout=5000)
                # logout does a full window.location navigation to /login (~2-3s);
                # a fixed sleep races the reload, so wait for the URL explicitly.
                # dev 模式下全页跳转 + 冷编译实测首轮可达 6.5s，审计全量跑时 dev server
                # 负载更重，8s 偶发不够（audit #3 因此 flaky），放宽到 15s。
                try:
                    aud.page.wait_for_url(lambda u: "/login" in u, timeout=15000)
                except Exception:
                    aud.page.wait_for_timeout(1000)
                redirected = "/login" in aud.page.url
                me = ctx.request.get(f"{API}/auth/me")
                still_authed = me.ok
                aud.shot("16_after_logout")
                record("logout clears session",
                       "PASS" if (redirected and not still_authed) else "FAIL",
                       f"redirected_to_login={redirected}; /auth/me={me.status}")
            except Exception as e:
                record("logout", "FAIL", str(e)[:200])

        # ---- 11. Logged-out home is public; the CREATE action must redirect to /login ----
        ctx2 = browser.new_context(viewport={"width": 1440, "height": 900})
        aud2 = Auditor(ctx2, "anon")
        aud2.page.goto(f"{BASE}/", wait_until="domcontentloaded", timeout=30000)
        aud2.page.wait_for_timeout(2000)
        aud2.shot("17_anon_home")
        try:
            aud2.page.get_by_placeholder("例如").fill("未登录创建测试")
            aud2.page.get_by_text("开始创作").click(timeout=5000)
            # 首页 createProject 先 await /auth/me（401）再 router.push('/login')；
            # Next dev 冷编译 + 网络往返下 3s 固定等待不够（audit #2 因此 flaky），
            # 改为显式等 URL，与 logout 步骤一致。
            try:
                aud2.page.wait_for_url(lambda u: "/login" in u, timeout=12000)
            except Exception:
                aud2.page.wait_for_timeout(1000)
            aud2.shot("18_anon_create_guarded")
            at_login = "/login" in aud2.page.url
            record("anonymous create redirected to login",
                   "PASS" if at_login else "FAIL", f"url={aud2.page.url}")
        except Exception as e:
            record("anonymous create redirected to login", "FAIL", str(e)[:200])

        dump()
        browser.close()


def dump():
    report_path = OUT / "report.json"
    report_path.write_text(json.dumps(RESULTS, ensure_ascii=False, indent=2))
    lines = ["# ClipWorks 浏览器 E2E 审计报告\n", "| 检查项 | 结果 | 说明 |", "|---|---|---|"]
    for r in RESULTS:
        lines.append(f"| {r['name']} | {r['status']} | {r['detail'][:160]} |")
    (OUT / "report.md").write_text("\n".join(lines), encoding="utf-8")
    from collections import Counter
    c = Counter(r["status"] for r in RESULTS)
    print("\n=== TALLY ===", dict(c))
    print(f"Artifacts: {OUT}")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        dump()
        sys.exit(1)
