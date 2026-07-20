"""Verify the Agent chat modifier fast-path: add text / delete last / recolor.

The deterministic fast-path runs before the LLM, so these are instant and stable.
render:false is passed so no render jobs are queued.

Run: .e2e-venv/bin/python scripts/e2e_modifier.py
"""
import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

BASE = "http://localhost:3000"
API = "http://localhost:8000"
OUT = Path("/Users/edwinhao/ClipWorks/data/e2e_audit")
UNSUPPORTED_HINT = "我目前能直接处理"


def main():
    ok = True
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        ctx.request.post(f"{API}/auth/mock-login?provider=google")

        fresh = ctx.request.post(
            f"{API}/projects/",
            headers={"Content-Type": "application/json"},
            data=json.dumps({"title": "e2e-modifier", "source_url": "", "source_type": "url"}),
        )
        pid = fresh.json()["id"]

        def comp():
            return ctx.request.get(f"{API}/compositions/{pid}").json()

        def total_clips():
            return sum(len(t["clips"]) for t in comp()["tracks"])

        def has_text(txt):
            for t in comp()["tracks"]:
                for c in t["clips"]:
                    if c.get("text_content") == txt:
                        return True
            return False

        def chat(message):
            r = ctx.request.post(
                f"{API}/projects/{pid}/agent/chat",
                headers={"Content-Type": "application/json"},
                data=json.dumps({"message": message, "render": False}),
            )
            return r.json()

        base = total_clips()

        # 1) add a text clip
        r1 = chat("添加文字：你好世界")
        add_ok = (
            UNSUPPORTED_HINT not in r1.get("reply", "")
            and total_clips() == base + 1
            and has_text("你好世界")
        )
        print("ADD_TEXT", "PASS" if add_ok else "FAIL",
              f"clips {base}->{total_clips()} reply={r1.get('reply')!r}")
        ok = ok and add_ok

        # 2) delete the last clip (the one just added, highest start_time)
        r2 = chat("删除最后一个片段")
        del_ok = (
            UNSUPPORTED_HINT not in r2.get("reply", "")
            and total_clips() == base
            and not has_text("你好世界")
        )
        print("DELETE_LAST", "PASS" if del_ok else "FAIL",
              f"clips={total_clips()} want {base} reply={r2.get('reply')!r}")
        ok = ok and del_ok

        # 3) regression: recolor still applies via fast-path
        r3 = chat("把画面变红")
        recolored = any(
            (c.get("style") or {}).get("color") == "#ef4444"
            for t in comp()["tracks"] for c in t["clips"]
        )
        red_ok = UNSUPPORTED_HINT not in r3.get("reply", "") and recolored
        print("RECOLOR", "PASS" if red_ok else "FAIL", f"reply={r3.get('reply')!r} recolored={recolored}")
        ok = ok and red_ok

        # light browser touch so the audit stays browser-flavored
        page = ctx.new_page(); page.set_default_timeout(15000)
        page.goto(f"{BASE}/projects/{pid}", wait_until="domcontentloaded")
        try: page.wait_for_load_state("networkidle", timeout=8000)
        except Exception: pass
        page.wait_for_timeout(1200)
        page.screenshot(path=str(OUT / "modifier_chat.png"), full_page=True)

        b.close()
    print("OVERALL", "PASS" if ok else "FAIL")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
